import os
import json
import logging
import asyncio
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Literal, Any, Dict
import pdfplumber
from dotenv import load_dotenv
import io
import edge_tts
import tempfile

load_dotenv()

app = FastAPI(title="CVFit API", version="1.0.0")

# Allow Next.js frontend (dev and prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from services.llm_provider import get_ai_provider, OllamaProvider

async def generate_with_retry_and_fallback(system_prompt: str, content: Any, response_model: type, max_retries: int = 2):
    """
    Tries multiple providers in order. For each provider, retries up to `max_retries` times.
    If a provider fails all retries, it switches to the next one.
    """
    providers = ["gemini", "ollama"]
    last_error = None
    
    for provider_name in providers:
        try:
            provider = get_ai_provider(provider_name)
        except Exception as e:
            logging.error(f"Failed to load provider {provider_name}: {e}")
            continue
            
        for attempt in range(max_retries):
            try:
                result = await provider.generate_structured(system_prompt, content, response_model)
                if result is not None:
                    return result
                raise Exception(f"{provider_name} returned None")
            except Exception as e:
                last_error = e
                logging.warning(f"Attempt {attempt + 1}/{max_retries} with {provider_name} failed: {e}")
                await asyncio.sleep(1) # wait before retry
                
    raise HTTPException(status_code=502, detail=f"All AI providers failed. Last error: {last_error}")

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

# ---------------------------------------------------------------------------
# Pydantic models – /api/analyze-cv (structured output)
# ---------------------------------------------------------------------------

class SuggestedEdit(BaseModel):
    section: str          # e.g. "Kinh nghiệm làm việc", "Kỹ năng"
    original_text: str    # Exact text from the original CV that needs changing
    upgraded_text: str    # Rewritten, metric-driven replacement
    reason: str           # Short explanation in Vietnamese

class CVAnalysisResponse(BaseModel):
    match_score: int               # 0 to 100
    impact_score: int              # 1 to 10
    tone: str                      # Short phrase in Vietnamese e.g. "Tự tin, Chuyên nghiệp"
    missing_keywords: List[str]    # Up to 5 missing keywords
    suggested_edits: List[SuggestedEdit]  # 3 to 5 high-impact bullet rewrites


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
        data = await generate_with_retry_and_fallback(system_prompt, f"CV:\n{cv_text}\n\nJob Description:\n{jd_text}", MatchResult)
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
        "- BƯỚC 2: TẤT CẢ các mảng văn bản trả về (tone, reason, missing_keywords, v.v.) PHẢI viết bằng CHÍNH ngôn ngữ của CV đó.\n"
        "  Ví dụ: Nếu CV tiếng Anh -> Phản hồi 100% bằng tiếng Anh. Nếu CV tiếng Việt -> Phản hồi 100% bằng tiếng Việt.\n\n"
        "Cấu trúc dữ liệu:\n"
        "- match_score (0-100): đánh giá mức độ phù hợp tổng thể của CV với JD.\n"
        "- impact_score (1-10): đánh giá mức độ ấn tượng và tác động của các thành tích trong CV.\n"
        "- tone: cụm từ ngắn mô tả giọng văn (VD: \"Confident & Professional\" hoặc \"Chuyên nghiệp, Tập trung vào kết quả\").\n"
        "- missing_keywords: tối đa 5 từ khóa quan trọng có trong JD nhưng THIẾU trong CV.\n"
        "- suggested_edits: từ 3 đến 5 đề xuất chỉnh sửa cụ thể cho các bullet point YẾU NHẤT.\n"
        "  Với mỗi đề xuất:\n"
        "  + section: tên phần (VD: \"Experience\", \"Kinh nghiệm làm việc\")\n"
        "  + original_text: trích dẫn CHÍNH XÁC đoạn gốc cần cải thiện\n"
        "  + upgraded_text: phiên bản viết lại (cùng ngôn ngữ với CV)\n"
        "  + reason: giải thích ngắn gọn tại sao cần thay đổi (cùng ngôn ngữ với CV)\n"
        "Hãy trung thực, mang tính xây dựng và cung cấp kết quả ở định dạng JSON hợp lệ duy nhất."
    )

    user_content = f"CV của ứng viên:\n{extracted_text}\n\nMô tả Công việc (JD):\n{jd_text}"

    # 3. Call Language Model with structured output
    try:
        parsed = await generate_with_retry_and_fallback(system_prompt, user_content, CVAnalysisResponse)
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
    """
    system_prompt = f"""You are Bé Đậu, a friendly but rigorous Senior Tech Recruiter in Vietnam. 
        You are conducting a professional 1-on-1 mock interview with a candidate.

        [CONTEXT]
        Job Description (JD):\n{req.jd_text}\n
        Candidate's CV:\n{req.cv_text}\n[RULES]
        1. Ask ONLY ONE question at a time. Keep it conversational but professional.
        2. Do NOT break character. Always respond entirely in natural Vietnamese.
        3. Read the candidate's latest answer in the chat history, then provide your response strictly matching the required JSON schema.

        [OUTPUT FIELDS EXPLANATION]
        - 'ai_feedback' (String): Brief, constructive micro-feedback on their previous answer. Point out what was good and what was missing. (If this is the first turn, output a warm welcome message here).
        - 'next_question' (String): The next interview question. Progress logically from introduction -> technical deep-dive (based on CV) -> behavioral (situational).
        - 'hint_for_user' (String): A short, actionable "cheat" hint on how to answer the 'next_question' (e.g., "Gợi ý: Hãy áp dụng cấu trúc STAR và nhắc đến công nghệ X bạn đã dùng ở công ty cũ.").[METRICS EVALUATION RULES]
        You must calculate 'metrics' based strictly on the candidate's latest answer:
        - 'confidence_score' (Integer, Range: 0 to 100): Evaluate textual fluency and decisiveness. 
        * 90-100: Clear, articulate, straight to the point.
        * 50-89: Normal speech, but slightly vague.
        * 0-49: Penalize heavily if the text contains filler words ("ờ", "ừm", "à", "thì là"), stuttering, or is excessively short.
        - 'confidence_feedback' (String): 1 short sentence explaining why you gave this confidence score.
        - 'jd_relevance_score' (Integer, Range: 0 to 100): How strongly the candidate's answer demonstrates the specific skills required in the JD. (e.g., 100 if they perfectly map their experience to a JD requirement).
        - 'jd_relevance_feedback' (String): 1 short sentence explaining the relevance score.
        - 'tech_vocab_rating' (String): MUST be exactly one of these 4 values:["YẾU", "KHÁ", "TỐT", "XUẤT SẮC"]. Evaluate their accurate use of professional and technical terminology.
        """

    contents = []
    for msg in req.chat_history:
        role = "model" if msg.role == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg.content}]})

    if not contents:
        # First turn logic setup since chat history is empty
        system_prompt += (
            "\n\nThis is the very first message of the interview. "
            "Introduce yourself formally as Bé Đậu, briefly summarize the JD, and ask the first introductory question. "
            "Leave 'ai_feedback' empty (\"\"), and initialize scores at 100. "
            "Provide a 'hint_for_user' on how to answer the first question."
        )
        # Push default startup cue for the LLMs since content is blank 
        contents = [{"role": "user", "parts": [{"text": "Xin chào, tôi đã sẵn sàng tham gia buổi phỏng vấn."}]}]

    try:
        parsed = await generate_with_retry_and_fallback(system_prompt, contents, InterviewTurnResponse)
        return parsed
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI Provider error: {e}")

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
