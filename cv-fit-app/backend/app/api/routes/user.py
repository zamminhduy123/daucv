"""
User-facing API routes — CV analysis, interview, TTS, and writing assistant.

Route handlers are kept thin: validate input → build prompt → call service → return.
"""

import json
import tempfile

import edge_tts
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import PDF_MAX_SIZE
from app.models.domain import MatchResult
from app.models.requests import (
    AnalyzeCVRequest,
    InterviewChatRequest,
    InterviewFinishRequest,
    ParseProfileRequest,
    TTSRequest,
    WriterRequest,
)
from app.models.responses import (
    CandidateProfileResponse,
    CVAnalysisLLMResponse,
    CVAnalysisResponse,
    FinalInterviewReport,
    InterviewTurnResponse,
    WriterResponse,
)
from app.prompts.system_prompts import (
    CV_ANALYSIS_CONTEXT_WITH_JD,
    CV_ANALYSIS_CONTEXT_WITHOUT_JD,
    INTERVIEW_FIRST_TURN_ADDENDUM,
    PERSONA_INSTRUCTIONS,
    ROUND_LABELS,
    build_cv_analysis_prompt,
    build_interview_chat_prompt,
    build_interview_finish_prompt,
    build_job_parser_prompt,
    build_upload_and_match_prompt,
    build_writer_prompt,
)
from app.services.ai_service import call_llm_with_fallback
from app.services.cv_quality_checks import build_scored_analysis
from app.utils.helpers import extract_text_from_pdf

router = APIRouter(prefix="/api", tags=["user"])


# ---------------------------------------------------------------------------
# POST /api/upload-and-match
# ---------------------------------------------------------------------------


@router.post("/upload-and-match", response_model=MatchResult)
async def upload_and_match(
    background_tasks: BackgroundTasks,
    cv_file: UploadFile = File(...),
    jd_text: str = Form(""),
):
    """
    Parse the uploaded CV PDF, compare with the JD, and return:
    - match_score  (0–100)
    - missing_skills  (list of strings)
    - tailored_cv  (rewritten resume JSON)
    """
    if cv_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    if cv_file.size is not None and cv_file.size > PDF_MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"PDF too large. Maximum size is {PDF_MAX_SIZE // (1024 * 1024)} MB.",
        )

    file_bytes = await cv_file.read()
    try:
        cv_text = extract_text_from_pdf(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse PDF: {e}")

    if not cv_text:
        raise HTTPException(
            status_code=422, detail="PDF appears to be empty or image-only."
        )

    system_prompt = build_upload_and_match_prompt()

    try:
        data = await call_llm_with_fallback(
            system_prompt,
            f"CV:\n{cv_text}\n\nJob Description:\n{jd_text}",
            MatchResult,
            feature_name="upload_and_match",
            prompt_version="1.0.0",
            background_tasks=background_tasks,
        )
        return data
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"AI returned invalid JSON: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")


# ---------------------------------------------------------------------------
# POST /api/extract-pdf
# ---------------------------------------------------------------------------


@router.post("/extract-pdf")
async def extract_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    if file.size is not None and file.size > PDF_MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"PDF too large. Maximum size is {PDF_MAX_SIZE // (1024 * 1024)} MB.",
        )
    try:
        file_bytes = await file.read()
        text = extract_text_from_pdf(file_bytes)
        return {"text": text}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# POST /api/analyze-cv
# ---------------------------------------------------------------------------


@router.post("/analyze-cv", response_model=CVAnalysisResponse)
async def analyze_cv(req: AnalyzeCVRequest, background_tasks: BackgroundTasks):
    """
    Accept raw CV text and a Job Description.
    Return a structured analysis.
    """
    extracted_text = req.cv_text.strip()
    jd_text = req.jd_text

    if not extracted_text:
        raise HTTPException(
            status_code=422,
            detail="Cần cung cấp nội dung CV.",
        )

    if jd_text.strip():
        context_instruction = CV_ANALYSIS_CONTEXT_WITH_JD
        user_content = (
            f"CV của ứng viên:\n{extracted_text}\n\nMô tả Công việc (JD):\n{jd_text}"
        )
    else:
        context_instruction = CV_ANALYSIS_CONTEXT_WITHOUT_JD
        user_content = f"CV của ứng viên:\n{extracted_text}"

    system_prompt = build_cv_analysis_prompt(context_instruction)

    try:
        parsed = await call_llm_with_fallback(
            system_prompt,
            user_content,
            CVAnalysisLLMResponse,
            feature_name="cv_analyzer",
            prompt_version="1.0.0",
            background_tasks=background_tasks,
        )
        return build_scored_analysis(parsed)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {e}",
        )


# ---------------------------------------------------------------------------
# POST /api/jobs/parse-profile
# ---------------------------------------------------------------------------


@router.post("/jobs/parse-profile", response_model=CandidateProfileResponse)
async def parse_profile(req: ParseProfileRequest, background_tasks: BackgroundTasks):
    """
    Parse candidate CV to get structured profile + search queries using LLM.
    """
    cv_text = req.cv_text.strip()
    if not cv_text:
        raise HTTPException(
            status_code=422,
            detail="Nội dung CV không được để trống.",
        )

    system_prompt = build_job_parser_prompt()
    user_content = f"Nội dung CV:\n{cv_text}"

    try:
        parsed = await call_llm_with_fallback(
            system_prompt,
            user_content,
            CandidateProfileResponse,
            feature_name="job_parser",
            prompt_version="1.0.0",
            background_tasks=background_tasks,
        )
        return parsed
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Profile parsing failed: {e}",
        )


# ---------------------------------------------------------------------------
# POST /api/interview/chat
# ---------------------------------------------------------------------------


@router.post("/interview/chat", response_model=InterviewTurnResponse)
async def interview_chat(req: InterviewChatRequest, background_tasks: BackgroundTasks):
    """
    Stateless mock interview turn processor mapping an InterviewChatRequest to an InterviewTurnResponse.
    Supports bounded interviews with question progress tracking.
    """
    active_persona = PERSONA_INSTRUCTIONS.get(
        req.interview_type, PERSONA_INSTRUCTIONS["general"]
    )

    # --- Dynamic question strategy based on progress ---
    if req.current_question == 1:
        question_strategy = "Ask an introductory/ice-breaker question to warm up the candidate. Keep it light but professional."
    elif req.current_question == req.total_questions:
        question_strategy = "This is the FINAL question. Ask a wrap-up or high-level culture-fit question (e.g., career goals, team values, why this company)."
    else:
        if req.interview_type == "hr":
            question_strategy = (
                "Ask a behavioral question to explore the candidate's responsibilities in past projects, "
                "teamwork, conflict resolution, or soft skills. Keep it relevant to their role but do not ask "
                "for low-level technical/coding implementation details or specific code techniques."
            )
        elif req.interview_type == "manager":
            question_strategy = (
                "Deep dive into project ownership, handling pressure/conflicts, business impact, "
                "and leadership/collaboration."
            )
        elif req.interview_type == "technical":
            question_strategy = (
                "Deep dive into a specific technical or situational requirement from the JD. "
                "Challenge the candidate on tools, frameworks, and system design."
            )
        else:
            # general or fallback
            question_strategy = (
                "Ask a balanced question covering a mix of professional experience, high-level technical alignment, "
                "or situational soft skills."
            )

    if req.jd_text.strip():
        jd_context = (
            f"You are interviewing the candidate for this specific JD:\n{req.jd_text}"
        )
    else:
        jd_context = "The candidate did not provide a specific JD. Conduct a general interview based purely on their CV to assess their past experiences, strengths, and general career readiness."

    system_prompt = build_interview_chat_prompt(
        active_persona=active_persona,
        jd_context=jd_context,
        cv_text=req.cv_text,
        current_question=req.current_question,
        total_questions=req.total_questions,
        question_strategy=question_strategy,
    )

    contents = []
    for msg in req.chat_history:
        contents.append(
            {
                "role": "assistant" if msg.role == "assistant" else "user",
                "content": msg.content,
            }
        )

    if not contents:
        # First turn logic setup since chat history is empty
        system_prompt += INTERVIEW_FIRST_TURN_ADDENDUM
        # Push default startup cue for the LLMs since content is blank
        contents = [
            {
                "role": "user",
                "content": "Xin chào, tôi đã sẵn sàng tham gia buổi phỏng vấn.",
            }
        ]

    try:
        parsed = await call_llm_with_fallback(
            system_prompt,
            contents,
            InterviewTurnResponse,
            feature_name="mock_interview",
            prompt_version="1.0.0",
            background_tasks=background_tasks,
        )
        return parsed
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI Provider error: {e}")


# ---------------------------------------------------------------------------
# POST /api/interview/finish — Final Assessment Report
# ---------------------------------------------------------------------------


@router.post("/interview/finish", response_model=FinalInterviewReport)
async def interview_finish(
    req: InterviewFinishRequest, background_tasks: BackgroundTasks
):
    """
    Takes the completed chat history and generates a comprehensive
    Final Assessment report with per-turn analysis.
    """
    if not req.chat_history:
        raise HTTPException(
            status_code=422, detail="Chat history is empty. Cannot generate report."
        )

    round_label = ROUND_LABELS.get(req.interview_type, ROUND_LABELS["general"])

    if req.jd_text.strip():
        jd_context = f"Job Description (JD):\n{req.jd_text}\n"
    else:
        jd_context = "The candidate did not provide a specific JD. Evaluate their performance purely based on their CV claims, general career readiness, and industry standards.\n"

    system_prompt = build_interview_finish_prompt(
        jd_context=jd_context,
        cv_text=req.cv_text,
        round_label=round_label,
    )

    contents = []
    for msg in req.chat_history:
        contents.append(
            {
                "role": "assistant" if msg.role == "assistant" else "user",
                "content": msg.content,
            }
        )

    try:
        parsed = await call_llm_with_fallback(
            system_prompt,
            contents,
            FinalInterviewReport,
            feature_name="interview_finish",
            prompt_version="1.0.0",
            background_tasks=background_tasks,
        )
        return parsed
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"Final assessment generation failed: {e}"
        )


# ---------------------------------------------------------------------------
# POST /api/interview/tts
# ---------------------------------------------------------------------------


@router.post("/interview/tts")
async def generate_tts(req: TTSRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    try:
        # Note: vi-VN-HoaiMyNeural seems to have downtime/restrictions causing NoAudioReceived
        # using vi-VN-NamMinhNeural as it successfully generates audio
        communicate = edge_tts.Communicate(req.text, "vi-VN-NamMinhNeural")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_path = tmp_file.name
        await communicate.save(tmp_path)
        return FileResponse(tmp_path, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST /api/writer/generate — Writing Assistant
# ---------------------------------------------------------------------------


@router.post("/writer/generate", response_model=WriterResponse)
async def writer_generate(req: WriterRequest, background_tasks: BackgroundTasks):
    """
    Generate an application email, cover letter, LinkedIn message, Zalo message,
    or custom writing based on the user's CV and JD.
    """
    if not req.cv_text.strip():
        raise HTTPException(status_code=422, detail="CV is required.")

    system_prompt = build_writer_prompt(
        writing_type=req.writing_type,
        tone=req.tone,
        jd_text=req.jd_text,
        custom_prompt=req.custom_prompt,
    )

    if req.jd_text.strip():
        user_content = (
            f"CV của ứng viên:\n{req.cv_text}\n\nMô tả Công việc (JD):\n{req.jd_text}"
        )
    else:
        user_content = f"CV của ứng viên:\n{req.cv_text}"

    try:
        parsed = await call_llm_with_fallback(
            system_prompt,
            user_content,
            WriterResponse,
            feature_name="writing_assistant",
            prompt_version="1.0.0",
            background_tasks=background_tasks,
        )
        return parsed
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Writer generation failed: {e}")
