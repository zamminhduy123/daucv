import os
import json
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import pdfplumber
from google import genai
from dotenv import load_dotenv
import io

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

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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

class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str

class InterviewRequest(BaseModel):
    jd_text: str
    cv_text: str
    chat_history: List[ChatMessage]

class InterviewResponse(BaseModel):
    response: str

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
        completion = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=f"CV:\n{cv_text}\n\nJob Description:\n{jd_text}",
            config={
                "system_instruction": system_prompt,
                "temperature": 0.3,
                "response_mime_type": "application/json",
            }
        )
        raw = completion.text or "{}"
        data = json.loads(raw)
        return MatchResult(**data)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"AI returned invalid JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini error: {e}")


# ---------------------------------------------------------------------------
# POST /api/analyze-cv
# ---------------------------------------------------------------------------

@app.post("/api/analyze-cv", response_model=CVAnalysisResponse)
async def analyze_cv(
    jd_text: str = Form(...),
    file: Optional[UploadFile] = File(None),
    cv_text: Optional[str] = Form(None),
):
    """
    Accept an optional PDF CV or raw CV text, and a Job Description. 
    Return a structured analysis.
    """
    # 1. Get CV text
    extracted_text = ""
    if file:
        file_bytes = await file.read()
        try:
            extracted_text = extract_text_from_pdf(file_bytes)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Không thể đọc file PDF: {e}")
    elif cv_text:
        extracted_text = cv_text.strip()

    if not extracted_text:
        raise HTTPException(
            status_code=422,
            detail="Cần cung cấp file PDF hoặc nội dung CV.",
        )

    # 2. Build system prompt
    system_prompt = (
        "Bạn là một Senior Tech Recruiter người Việt Nam với hơn 10 năm kinh nghiệm tuyển dụng "
        "tại các công ty công nghệ hàng đầu. Bạn nổi tiếng là thẳng thắn, trực tiếp nhưng luôn "
        "mang tính xây dựng.\n\n"
        "Nhiệm vụ: Phân tích CV ứng viên dựa trên Mô tả Công việc (JD) được cung cấp và trả về "
        "kết quả phân tích chi tiết theo cấu trúc yêu cầu.\n\n"
        "Quy tắc bắt buộc:\n"
        "- Tất cả các phản hồi (tone, reason, missing_keywords, v.v.) PHẢI được viết bằng tiếng Việt.\n"
        "- match_score (0-100): đánh giá mức độ phù hợp tổng thể của CV với JD.\n"
        "- impact_score (1-10): đánh giá mức độ ấn tượng và tác động của các thành tích trong CV.\n"
        "- tone: một cụm từ ngắn mô tả giọng văn của CV (ví dụ: \"Tự tin, Chuyên nghiệp\").\n"
        "- missing_keywords: tối đa 5 từ khóa/kỹ năng quan trọng có trong JD nhưng THIẾU trong CV.\n"
        "- suggested_edits: từ 3 đến 5 đề xuất chỉnh sửa cụ thể cho các bullet point YẾU NHẤT trong CV.\n"
        "  Với mỗi đề xuất:\n"
        "  + section: tên phần CV (ví dụ: \"Kinh nghiệm làm việc\", \"Kỹ năng\")\n"
        "  + original_text: trích dẫn CHÍNH XÁC đoạn văn bản gốc từ CV cần thay đổi\n"
        "  + upgraded_text: phiên bản viết lại, có số liệu cụ thể, phù hợp với JD\n"
        "  + reason: giải thích ngắn gọn tại sao cần thay đổi (bằng tiếng Việt)\n"
        "Hãy trung thực và mang tính xây dựng. Ưu tiên những chỉnh sửa có tác động lớn nhất."
    )

    user_content = f"CV của ứng viên:\n{extracted_text}\n\nMô tả Công việc (JD):\n{jd_text}"

    # 3. Call Gemini with structured output
    try:
        # completion = client.models.generate_content(
        #     model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        #     contents=user_content,
        #     config={
        #         "system_instruction": system_prompt,
        #         "temperature": 0.3,
        #         "response_mime_type": "application/json",
        #         "response_schema": CVAnalysisResponse,
        #     }
        # )
        # parsed = completion.parsed
        # if parsed is None:
        #     raise Exception("Gemini return empty")
        # return parsed

        # simulate gemini fail
        raise Exception("Gemini return empty")
    except Exception as e:
        print(f"Gemini error: {e}. Trying Ollama fallback...")
        # Fallback to Ollama gemma4:e4b
        import httpx
        try:
            async with httpx.AsyncClient() as http_client:
                fallback_prompt = f"""{system_prompt}
                CRITICAL: Answer ONLY with pure JSON.
                
                CV content:
                {user_content}"""
                
                # Use /api/chat if sending messages
                res = await http_client.post(
                    "https://divorcee-work-pessimism.ngrok-free.dev/ollama/api/generate",
                    json={
                        "model": "gemma4:e4b",
                        "prompt": fallback_prompt,
                        "format": CVAnalysisResponse.model_json_schema(),
                        "stream": False,
                        "options": {
                            "temperature": 0.3  # Keep low for consistency
                        }
                    },
                    timeout=300.0
                )
                res.raise_for_status()
                ollama_data = res.json()
                raw_content = ollama_data.get("response", {})
                parsed_json = json.loads(raw_content)
                return CVAnalysisResponse(**parsed_json)
        except Exception as ollama_e:
            raise HTTPException(
                status_code=500, 
                detail=f"Gemini error: {e}. Ollama fallback error: {ollama_e}"
            )


@app.post("/api/interview/chat", response_model=InterviewResponse)
async def interview_chat(req: InterviewRequest):
    """
    Continue the mock interview. Accepts full chat history and returns the
    AI interviewer's next message.
    """
    system_prompt = (
        "Bạn là Bé Đậu - người phỏng vấn AI thông minh và thân thiện. "
        "Bạn đang giúp ứng viên luyện tập cho vị trí công việc dựa trên JD và CV dưới đây.\n"
        f"JD:\n{req.jd_text}\n\nCV Ứng viên:\n{req.cv_text}\n\n"
        "Nguyên tắc:\n"
        "- Nói chuyện thân thiện, khuyến khích như một người bạn (Career Coach).\n"
        "- Phỏng vấn NGHIÊM NGẶT bằng tiếng Việt.\n"
        "- Mỗi lần chỉ đặt MỘT câu hỏi (kỹ thuật hoặc tình huống dựa trên JD).\n"
        "- Đưa ra nhận xét ngắn gọn về câu trả lời trước đó (khen ngợi hoặc góp ý) trước khi hỏi câu tiếp theo.\n"
        "- Giữ tông giọng chuyên nghiệp nhưng không gò bó.\n"
        "- Nếu là tin nhắn đầu tiên, hãy chào mừng ứng viên bằng giọng của Bé Đậu và bắt đầu câu hỏi đầu tiên.\n"
        "- Sau khoảng 5-6 câu hỏi, hãy đưa ra bản tóm tắt nhận xét và kết thúc buổi phỏng vấn."
    )



    contents = []
    for msg in req.chat_history:
        # "user" maps to "user", "assistant" maps to "model" for Gemini
        role = "model" if msg.role == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg.content}]})

    try:
        completion = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=contents,
            config={
                "system_instruction": system_prompt,
                "temperature": 0.7,
            }
        )
        return InterviewResponse(response=completion.text or "")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini error: {e}")
