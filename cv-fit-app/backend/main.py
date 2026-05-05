import os
import json
import logging
import asyncio
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from typing import List, Optional, Literal, Any, Dict
import pdfplumber
from dotenv import load_dotenv
import io
import edge_tts
import tempfile
from openai import AsyncOpenAI

load_dotenv()

app = FastAPI(title="CVFit API", version="1.0.0")

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "CVFit API is running"}

# Allow Next.js frontend (dev and prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# LLM Unified Fallback Configuration
# ---------------------------------------------------------------------------

PROVIDERS = [
    {
        "name": "Gemini",
        "client": AsyncOpenAI(api_key=os.getenv("GEMINI_API_KEY", "dummy"), base_url="https://generativelanguage.googleapis.com/v1beta/openai/"),
        "model": "gemini-2.5-flash"
    },
    {
        "name": "Groq",
        "client": AsyncOpenAI(api_key=os.getenv("GROQ_API_KEY", "dummy"), base_url="https://api.groq.com/openai/v1"),
        "model": "llama-3.3-70b-versatile"
    },
    {
        "name": "OpenRouter",
        "client": AsyncOpenAI(api_key=os.getenv("OPENROUTER_API_KEY", "dummy"), base_url="https://openrouter.ai/api/v1"),
        "model": "google/gemini-2.5-flash"
    }
]

async def call_llm_with_fallback(system_prompt: str, user_input: Any, response_model: type, max_retries: int = 1):
    """
    Tries multiple providers in a waterfall logic. 
    If a provider fails, switches to the next one.
    """
    if "JSON" not in system_prompt.upper():
        system_prompt += "\n\nYou must return a valid JSON object matching the exact requested schema."

    messages = [{"role": "system", "content": system_prompt}]
    
    if isinstance(user_input, str):
        messages.append({"role": "user", "content": user_input})
    elif isinstance(user_input, list):
        messages.extend(user_input)

    last_error = None
    
    for provider in PROVIDERS:
        client: AsyncOpenAI = provider["client"]
        model: str = provider["model"]
        name: str = provider["name"]
        
        for attempt in range(max_retries):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.7
                )
                
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Empty response content")
                
                parsed = response_model.model_validate_json(content)
                return parsed
                
            except Exception as e:
                last_error = str(e)
                logging.warning(f"Provider {name} attempt {attempt + 1} failed: {last_error}. Switching to next...")
                await asyncio.sleep(1) # wait before retry
                
    raise HTTPException(status_code=503, detail=f"All AI providers are currently overloaded. Last error: {last_error}")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF file."""
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
    return text.strip()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ExperienceItem(BaseModel):
    company: str
    role: str
    bullet_points: List[str]

class TailoredCV(BaseModel):
    name: str
    summary: str
    experience: List[ExperienceItem]
    education: str
    skills: List[str]

class MatchResult(BaseModel):
    match_score: int
    missing_skills: List[str]
    tailored_cv: TailoredCV

class Message(BaseModel):
    role: str   # "user" | "assistant"
    content: str

class InterviewChatRequest(BaseModel):
    jd_text: str
    cv_text: str
    chat_history: List[Message]
    current_question: int = 1      # e.g., 1
    total_questions: int = 5       # e.g., 5

class LiveMetrics(BaseModel):
    confidence_score: int
    confidence_feedback: str
    jd_relevance_score: int
    jd_relevance_feedback: str
    tech_vocab_rating: Literal["YẾU", "KHÁ", "TỐT", "XUẤT SẮC"]

class InterviewTurnResponse(BaseModel):
    ai_feedback: str
    next_question: str
    hint_for_user: str
    metrics: LiveMetrics

class TurnAnalysis(BaseModel):
    question: str
    user_answer: str
    feedback: str                   # What they did well and what they missed
    ideal_answer_snippet: str       # "Ví dụ cách trả lời ghi điểm: ..."

class SubScore(BaseModel):
    category: str # "Kỹ năng chuyên môn", "Giải quyết vấn đề", "Kiến thức ngành", "Giao tiếp", "Thái độ & Hành vi"
    score: int # 0-100
    label: str # "Xuất sắc", "Tốt", "Khá", "Cần cố gắng"

class AIFeedbackSummary(BaseModel):
    positive: str # "Great logical thinking..."
    warning: str # "Try to communicate your thought process more clearly."
    actionable: str # "Practice more system design concepts."

class FinalInterviewReport(BaseModel):
    overall_score: int              # 0-100
    overall_feedback: str           # 2-3 sentences summarizing performance
    sub_scores: List[SubScore]      # Exactly 5 items matching the categories above
    key_strengths: List[str]        # 2-3 bullet points
    areas_for_improvement: List[str] # 2-3 bullet points
    top_topics_covered: List[str]   # e.g., ["React", "State Management", "Behavioral"]
    ai_feedback_summary: AIFeedbackSummary
    turn_by_turn_analysis: List[TurnAnalysis]

class InterviewFinishRequest(BaseModel):
    jd_text: str
    cv_text: str
    chat_history: List[Message]

# ---------------------------------------------------------------------------
# Pydantic models – /api/analyze-cv (structured output)
# ---------------------------------------------------------------------------

class SuggestedEdit(BaseModel):
    section: str          # e.g. "Kinh nghiệm làm việc", "Kỹ năng"
    original_text: str    # Exact text from the original CV that needs changing
    upgraded_text: str    # Rewritten, metric-driven replacement
    reason: str           # Short explanation in Vietnamese

class PrioritizedKeyword(BaseModel):
    keyword: str
    priority: Literal["High", "Medium", "Low"]

class EvidenceAnalysis(BaseModel):
    claim: str              # e.g. "Scalable system delivery", "MLOps experience"
    evidence_strength: Literal["Strong", "Medium", "Weak", "Missing"]
    comment: str            # e.g. "Supported by 8M+ MAU", "Not visible in current CV"

class CVAnalysisResponse(BaseModel):
    match_score: int               # 0 to 100 - overall match
    match_headline: str            # e.g. "Rất phù hợp — Khả năng lọt vào vòng phỏng vấn cao."
    match_summary: str             # 2-3 sentences explaining the score and what to focus on

    # 6 sub-scores (all 0 to 100)
    technical_match: int
    experience_relevance: int
    keyword_coverage: int
    impact_evidence: int
    tone_quality: int
    ats_readiness: int

    missing_keywords: List[str]           # Up to 5 missing keywords
    suggested_edits: List[SuggestedEdit]  # 3 to 5 high-impact bullet rewrites

    # NEW: Widgets data
    cv_strengths: List[str]                          # 3-4 bullet points of what the CV does well
    prioritized_keywords: List[PrioritizedKeyword]   # Missing keywords with priority levels
    evidence_analysis: List[EvidenceAnalysis]         # 4-5 items evaluating claims vs evidence


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def health():
    return {"status": "ok", "message": "CVFit API is running"}


@app.post("/api/upload-and-match", response_model=MatchResult)
async def upload_and_match(
    cv_file: UploadFile = File(...),
    jd_text: str = Form(...),
):
    """
    Parse the uploaded CV PDF, compare with the JD, and return:
    - match_score  (0–100)
    - missing_skills  (list of strings)
    - tailored_cv  (rewritten resume JSON)
    """
    if cv_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    file_bytes = await cv_file.read()
    try:
        cv_text = extract_text_from_pdf(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse PDF: {e}")

    if not cv_text:
        raise HTTPException(status_code=422, detail="PDF appears to be empty or image-only.")

    system_prompt = (
        "Bạn là Bé Đậu - một chuyên gia nhân sự và người đồng hành (career coach) tận tâm tại thị trường Việt Nam. "
        "Hãy so sánh CV và Mô tả công việc (JD) dưới đây. "
        "Hãy trả về DUY NHẤT một đối tượng JSON với các khóa sau:\n"
        "  match_score: số nguyên 0-100 (Tỷ lệ ĐẬU dự kiến)\n"
        "  missing_skills: mảng các chuỗi (các kỹ năng trong JD nhưng thiếu trong CV, ghi bằng tiếng Việt)\n"
        "  tailored_cv: đối tượng gồm:\n"
        "    name: tên ứng viên\n"
        "    summary: tóm tắt (2-3 câu, tối ưu hóa theo JD, ghi bằng tiếng Việt)\n"
        "    experience: mảng các {company, role, bullet_points[]} "
        "(viết lại các gạch đầu dòng để làm nổi bật sự phù hợp với JD, ghi bằng tiếng Việt)\n"
        "    education: học vấn (ghi bằng tiếng Việt)\n"
        "    skills: mảng các chuỗi (kỹ năng ứng viên ĐÃ CÓ, ghi bằng tiếng Việt)\n"
        "Chỉ xuất JSON. Không giải thích thêm."
    )



    try:
        data = await call_llm_with_fallback(system_prompt, f"CV:\n{cv_text}\n\nJob Description:\n{jd_text}", MatchResult)
        return data
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"AI returned invalid JSON: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")


class AnalyzeCVRequest(BaseModel):
    jd_text: str
    cv_text: str

# ---------------------------------------------------------------------------
# POST /api/extract-pdf
# ---------------------------------------------------------------------------

@app.post("/api/extract-pdf")
async def extract_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    try:
        file_bytes = await file.read()
        text = extract_text_from_pdf(file_bytes)
        return {"text": text}
    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------------------------------------------
# POST /api/analyze-cv
# ---------------------------------------------------------------------------

@app.post("/api/analyze-cv", response_model=CVAnalysisResponse)
async def analyze_cv(req: AnalyzeCVRequest):
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

    # 2. Build system prompt
    system_prompt = (
        "Bạn là một Senior Tech Recruiter đóng vai trò chuyên gia review CV. Bạn thẳng thắn, trực tiếp và luôn mang tính xây dựng.\n\n"
        "Nhiệm vụ: Phân tích CV ứng viên dựa trên Mô tả Công việc (JD) được cung cấp và trả về kết quả phân tích.\n\n"
        "QUY TẮC BẮT BUỘC VỀ NGÔN NGỮ:\n"
        "- BƯỚC 1: Xác định ngôn ngữ chính của CV ứng viên (Tiếng Anh hoặc Tiếng Việt).\n"
        "- BƯỚC 2: TẤT CẢ các mảng văn bản trả về PHẢI viết bằng CHÍNH ngôn ngữ của CV đó.\n"
        "  Ví dụ: Nếu CV tiếng Anh -> Phản hồi 100% bằng tiếng Anh. Nếu CV tiếng Việt -> Phản hồi 100% bằng tiếng Việt.\n\n"
        "Cấu trúc JSON cần trả về (TẤT CẢ điểm số đều từ 0 đến 100):\n"
        "- match_score (0-100): Đánh giá mức độ phù hợp TỔNG THỂ của CV với JD.\n"
        "- match_headline: Câu tiêu đề ngắn gọn mô tả kết quả (VD: \"Rất phù hợp — Khả năng lọt vào vòng phỏng vấn cao.\" hoặc \"Cần cải thiện — CV chưa bám sát yêu cầu JD.\").\n"
        "- match_summary: 2-3 câu giải thích điểm số tổng thể và những điểm cần tập trung cải thiện nhất.\n"
        "- technical_match (0-100): Mức độ khớp về kỹ năng kỹ thuật / chuyên môn giữa CV và JD.\n"
        "- experience_relevance (0-100): Mức độ liên quan của kinh nghiệm làm việc với vị trí trong JD.\n"
        "- keyword_coverage (0-100): Tỷ lệ từ khóa quan trọng trong JD xuất hiện trong CV.\n"
        "- impact_evidence (0-100): Mức độ định lượng kết quả (metrics, số liệu cụ thể) trong các thành tích.\n"
        "- tone_quality (0-100): Chất lượng và tính chuyên nghiệp của giọng văn trong CV.\n"
        "- ats_readiness (0-100): Mức độ chuẩn định dạng ATS (không có bảng phức tạp, font chuẩn, heading rõ ràng).\n"
        "- missing_keywords: Mảng tối đa 5 từ khóa quan trọng có trong JD nhưng THIẾU trong CV.\n"
        "- suggested_edits: Từ 3 đến 5 đề xuất chỉnh sửa cụ thể cho các bullet point YẾU NHẤT.\n"
        "  Với mỗi đề xuất:\n"
        "  + section: tên phần (VD: \"Experience\", \"Kinh nghiệm làm việc\")\n"
        "  + original_text: trích dẫn CHÍNH XÁC đoạn gốc cần cải thiện\n"
        "  + upgraded_text: phiên bản viết lại (cùng ngôn ngữ với CV)\n"
        "  + reason: giải thích ngắn gọn tại sao cần thay đổi (cùng ngôn ngữ với CV)\n\n"
        "- cv_strengths: Mảng 3-4 điểm sáng / ưu điểm nổi bật của CV hiện tại (VD: \"Strong production engineering experience\", \"Professional and concise language\").\n"
        "- prioritized_keywords: Mảng từ khóa quan trọng CẦN BỔ SUNG, mỗi item gồm:\n"
        "  + keyword: tên từ khóa\n"
        "  + priority: PHẢI là một trong [\"High\", \"Medium\", \"Low\"] — \"High\" nếu từ khóa xuất hiện nhiều lần trong JD hoặc là yêu cầu bắt buộc, \"Low\" nếu chỉ là nice-to-have.\n"
        "- evidence_analysis: Mảng 4-5 năng lực/claim mà ứng viên thể hiện hoặc cần thể hiện, mỗi item gồm:\n"
        "  + claim: Năng lực / skill / claim được đánh giá (VD: \"Scalable system delivery\", \"MLOps experience\")\n"
        "  + evidence_strength: PHẢI là một trong [\"Strong\", \"Medium\", \"Weak\", \"Missing\"]\n"
        "    * \"Strong\": Có số liệu cụ thể, metrics, context rõ ràng hỗ trợ claim.\n"
        "    * \"Medium\": Có nhắc đến nhưng thiếu định lượng hoặc context cụ thể.\n"
        "    * \"Weak\": Nhắc đến mơ hồ, không có bằng chứng thực tế.\n"
        "    * \"Missing\": Hoàn toàn không tìm thấy bằng chứng nào trong CV.\n"
        "  + comment: Nhận xét ngắn gọn giải thích đánh giá (VD: \"Supported by 8M+ MAU metrics\", \"No leadership evidence found\")\n\n"
        "Hãy trung thực, mang tính xây dựng và cung cấp kết quả ở định dạng JSON hợp lệ duy nhất."
    )

    user_content = f"CV của ứng viên:\n{extracted_text}\n\nMô tả Công việc (JD):\n{jd_text}"

    # 3. Call Language Model with structured output
    try:
        parsed = await call_llm_with_fallback(system_prompt, user_content, CVAnalysisResponse)
        return parsed
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Analysis failed: {e}"
        )


@app.post("/api/interview/chat", response_model=InterviewTurnResponse)
async def interview_chat(req: InterviewChatRequest):
    """
    Stateless mock interview turn processor mapping an InterviewChatRequest to an InterviewTurnResponse.
    Supports bounded interviews with question progress tracking.
    """
    # --- Dynamic question strategy based on progress ---
    question_strategy = ""
    if req.current_question == 1:
        question_strategy = "Ask an introductory/ice-breaker question to warm up the candidate. Keep it light but professional."
    elif req.current_question == req.total_questions:
        question_strategy = "This is the FINAL question. Ask a wrap-up or high-level culture-fit question (e.g., career goals, team values, why this company)."
    else:
        question_strategy = "Deep dive into a specific technical or situational requirement from the JD. Challenge the candidate."

    system_prompt = f"""You are Bé Đậu, a friendly but rigorous Senior Tech Recruiter in Vietnam. 
        You are conducting a professional 1-on-1 mock interview with a candidate.

        [CONTEXT]
        Job Description (JD):\n{req.jd_text}\n
        Candidate's CV:\n{req.cv_text}\n
        [INTERVIEW PROGRESS]
        You are currently asking question {req.current_question} out of {req.total_questions}.
        Question strategy: {question_strategy}

        [RULES]
        1. Ask ONLY ONE question at a time. Keep it conversational but professional.
        2. Do NOT break character. Always respond entirely in natural Vietnamese.
        3. Read the candidate's latest answer in the chat history, then provide your response strictly matching the required JSON schema.
        4. Follow the [INTERVIEW PROGRESS] question strategy strictly.

        [OUTPUT FIELDS EXPLANATION]
        - 'ai_feedback' (String): Brief, constructive micro-feedback on their previous answer. Point out what was good and what was missing. (If this is the first turn, output a warm welcome message here).
        - 'next_question' (String): The next interview question. Follow the strategy in [INTERVIEW PROGRESS].
        - 'hint_for_user' (String): A short, actionable "cheat" hint on how to answer the 'next_question' (e.g., "Gợi ý: Hãy áp dụng cấu trúc STAR và nhắc đến công nghệ X bạn đã dùng ở công ty cũ.").
        - 'metrics' (Object): MUST contain the following fields based strictly on the candidate's latest answer. Output exactly as a nested JSON object:
            * 'confidence_score' (Integer, Range: 0 to 100): Evaluate textual fluency and decisiveness.
                - 90-100: Clear, articulate, straight to the point.
                - 50-89: Normal speech, but slightly vague.
                - 0-49: Penalize heavily if the text contains filler words ("ờ", "ừm", "à", "thì là"), stuttering, or is excessively short.
            * 'confidence_feedback' (String): 1 short sentence explaining why you gave this confidence score.
            * 'jd_relevance_score' (Integer, Range: 0 to 100): How strongly the candidate's answer demonstrates the specific skills required in the JD.
            * 'jd_relevance_feedback' (String): 1 short sentence explaining the relevance score.
            * 'tech_vocab_rating' (String): MUST be exactly one of these 4 values:["YẾU", "KHÁ", "TỐT", "XUẤT SẮC"]. Evaluate their accurate use of professional terminology.
        """

    contents = []
    for msg in req.chat_history:
        contents.append({"role": "assistant" if msg.role == "assistant" else "user", "content": msg.content})

    if not contents:
        # First turn logic setup since chat history is empty
        system_prompt += (
            "\n\nThis is the very first message of the interview. "
            "Introduce yourself formally as Bé Đậu, briefly summarize the JD, and ask the first introductory question. "
            "Leave 'ai_feedback' empty (\"\"), and initialize scores at 100. "
            "Provide a 'hint_for_user' on how to answer the first question."
        )
        # Push default startup cue for the LLMs since content is blank 
        contents = [{"role": "user", "content": "Xin chào, tôi đã sẵn sàng tham gia buổi phỏng vấn."}]

    try:
        parsed = await call_llm_with_fallback(system_prompt, contents, InterviewTurnResponse)
        return parsed
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI Provider error: {e}")


# ---------------------------------------------------------------------------
# POST /api/interview/finish — Final Assessment Report
# ---------------------------------------------------------------------------

@app.post("/api/interview/finish", response_model=FinalInterviewReport)
async def interview_finish(req: InterviewFinishRequest):
    """
    Takes the completed chat history and generates a comprehensive
    Final Assessment report with per-turn analysis.
    """
    if not req.chat_history:
        raise HTTPException(status_code=422, detail="Chat history is empty. Cannot generate report.")

    system_prompt = f"""You are a Senior Tech Recruiter conducting a post-interview evaluation.
        The mock interview has ENDED. Your task is to review the ENTIRE conversation and generate a comprehensive assessment report.

        [CONTEXT]
        Job Description (JD):\n{req.jd_text}\n
        Candidate's CV:\n{req.cv_text}\n
        [EVALUATION INSTRUCTIONS]
        1. Review every question-answer pair in the chat history.
        2. Evaluate the candidate's performance AGAINST the JD requirements and their CV claims.
        3. Be honest, constructive, and specific.
        4. Respond ENTIRELY in Vietnamese.

        [OUTPUT JSON SCHEMA]
        - 'overall_score' (Integer, 0-100): Overall interview performance score.
            * 85-100: Excellent — candidate clearly demonstrates fit.
            * 65-84: Good — solid answers but some gaps.
            * 40-64: Average — noticeable weaknesses.
            * 0-39: Below expectations — needs significant improvement.
        - 'overall_feedback' (String): 2-3 sentences summarizing the candidate's performance.
        - 'sub_scores' (Array of Objects): Exactly 5 items for these categories: "Kỹ năng chuyên môn", "Giải quyết vấn đề", "Kiến thức ngành", "Giao tiếp", "Thái độ & Hành vi". Each object has:
            * 'category' (String): The category name.
            * 'score' (Integer, 0-100): Score for this category.
            * 'label' (String): "Xuất sắc", "Tốt", "Khá", or "Cần cố gắng" based on the score.
        - 'key_strengths' (Array of Strings): 2-3 bullet points highlighting what the candidate did well.
        - 'areas_for_improvement' (Array of Strings): 2-3 bullet points on what needs work.
        - 'top_topics_covered' (Array of Strings): List 3-5 main topics discussed (e.g., ["React", "State Management", "Behavioral"]).
        - 'ai_feedback_summary' (Object): Containing exactly 3 fields:
            * 'positive' (String): e.g. "Great logical thinking and coding approach."
            * 'warning' (String): e.g. "Try to communicate your thought process more clearly."
            * 'actionable' (String): e.g. "Practice more system design and scalability concepts."
        - 'turn_by_turn_analysis' (Array of Objects): Output exactly as an array of JSON objects. For EACH question-answer pair in the chat, create an object with:
            * 'question' (String): The interviewer's question.
            * 'user_answer' (String): The candidate's answer (summarized if long).
            * 'feedback' (String): What they did well and what they missed.
            * 'ideal_answer_snippet' (String): "Ví dụ cách trả lời ghi điểm: ..." — a model answer snippet.
        """

    contents = []
    for msg in req.chat_history:
        contents.append({"role": "assistant" if msg.role == "assistant" else "user", "content": msg.content})

    try:
        parsed = await call_llm_with_fallback(system_prompt, contents, FinalInterviewReport)
        return parsed
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Final assessment generation failed: {e}")

class TTSRequest(BaseModel):
    text: str

@app.post("/api/interview/tts")
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

class WriterRequest(BaseModel):
    cv_text: str
    jd_text: str
    writing_type: str       # "email", "linkedin", "zalo", "custom"
    tone: str               # e.g. "Chuyên nghiệp", "Ngắn gọn", "Tự tin"
    custom_prompt: Optional[str] = None

class WriterResponse(BaseModel):
    subject_line: str       # Catchy subject line (empty if not applicable)
    content: str            # Main generated letter/message
    tips: List[str]         # 1-2 quick actionable tips

@app.post("/api/writer/generate", response_model=WriterResponse)
async def writer_generate(req: WriterRequest):
    """
    Generate an application email, cover letter, LinkedIn message, Zalo message,
    or custom writing based on the user's CV and JD.
    """
    if not req.cv_text.strip() or not req.jd_text.strip():
        raise HTTPException(status_code=422, detail="CV and JD are both required.")

    type_labels = {
        "email": "Email ứng tuyển (Application Email)",
        "linkedin": "Tin nhắn LinkedIn cho nhà tuyển dụng",
        "zalo": "Tin nhắn Zalo ngắn gọn cho HR",
        "custom": "Nội dung tùy chỉnh theo yêu cầu người dùng",
    }
    type_desc = type_labels.get(req.writing_type, req.writing_type)

    system_prompt = (
        "Bạn là một chuyên gia Tư vấn Nghề nghiệp (Career Coach) tại Việt Nam.\n\n"
        "QUY TẮC BẮT BUỘC VỀ NGÔN NGỮ:\n"
        "- BƯỚC 1: Xác định ngôn ngữ chính của CV ứng viên (Tiếng Anh hoặc Tiếng Việt).\n"
        "- BƯỚC 2: TẤT CẢ nội dung trả về PHẢI viết bằng CHÍNH ngôn ngữ của CV đó.\n\n"
        f"Nhiệm vụ: Viết một {type_desc} với giọng văn '{req.tone}' dựa trên CV và JD bên dưới.\n\n"
        "QUY TẮC QUAN TRỌNG:\n"
        "- KHÔNG bịa đặt kinh nghiệm hoặc kỹ năng mà CV không có.\n"
        "- Nội dung phải BÁM SÁT các yêu cầu trong JD.\n"
        "- Giữ ngắn gọn, chuyên nghiệp, và phù hợp với kênh giao tiếp.\n"
    )

    if req.writing_type == "zalo":
        system_prompt += (
            "- Tin nhắn Zalo phải NGẮN (dưới 150 từ), thân thiện nhưng chuyên nghiệp.\n"
            "- subject_line trả về chuỗi rỗng vì Zalo không có tiêu đề.\n"
        )
    elif req.writing_type == "linkedin":
        system_prompt += (
            "- Tin nhắn LinkedIn phải ngắn gọn (dưới 200 từ), chuyên nghiệp.\n"
            "- subject_line trả về chuỗi rỗng.\n"
        )
    elif req.writing_type == "email":
        system_prompt += (
            "- Email cần có subject_line hấp dẫn và chuyên nghiệp.\n"
            "- Nội dung email đầy đủ: lời chào, giới thiệu bản thân, lý do ứng tuyển, điểm mạnh phù hợp JD, lời kết.\n"
        )

    if req.writing_type == "custom" and req.custom_prompt:
        system_prompt += f"\nYÊU CẦU BỔ SUNG TỪ NGƯỜI DÙNG:\n{req.custom_prompt}\n"

    system_prompt += (
        "\nCấu trúc JSON cần trả về:\n"
        "- subject_line: Tiêu đề email (để rỗng nếu là tin nhắn Zalo/LinkedIn)\n"
        "- content: Nội dung chính của thư/tin nhắn\n"
        "- tips: Mảng 1-2 lời khuyên ngắn gọn (VD: 'Nhớ đính kèm link Portfolio vào cuối email.')\n"
        "Chỉ trả về JSON hợp lệ duy nhất."
    )

    user_content = f"CV của ứng viên:\n{req.cv_text}\n\nMô tả Công việc (JD):\n{req.jd_text}"

    try:
        parsed = await call_llm_with_fallback(system_prompt, user_content, WriterResponse)
        return parsed
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Writer generation failed: {e}")

