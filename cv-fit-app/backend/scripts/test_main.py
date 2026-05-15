import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import app from main
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "CVFit API is running"}

@patch("main.client.models.generate_content")
def test_interview_chat(mock_generate_content):
    # Set up the mock response to match InterviewTurnResponse
    mock_parsed = MagicMock()
    mock_parsed.ai_feedback = "Tốt lắm, bạn có giao tiếp rõ ràng."
    mock_parsed.next_question = "Bạn có kinh nghiệm với React không?"
    
    mock_metrics = MagicMock()
    mock_metrics.confidence_score = 95
    mock_metrics.confidence_feedback = "Giọng nói trôi chảy, lưu loát."
    mock_metrics.jd_relevance_score = 85
    mock_metrics.jd_relevance_feedback = "Trả lời sát với yêu cầu JD."
    mock_metrics.tech_vocab_rating = "TỐT"
    
    # Needs to be modeled as dictionary when converting to JSON by FastAPI/Pydantic
    mock_parsed.model_dump.return_value = {
        "ai_feedback": mock_parsed.ai_feedback,
        "next_question": mock_parsed.next_question,
        "metrics": {
            "confidence_score": mock_metrics.confidence_score,
            "confidence_feedback": mock_metrics.confidence_feedback,
            "jd_relevance_score": mock_metrics.jd_relevance_score,
            "jd_relevance_feedback": mock_metrics.jd_relevance_feedback,
            "tech_vocab_rating": mock_metrics.tech_vocab_rating,
        }
    }
    # FastAPI test client expects Pydantic models when directly returning `parsed`, but mocked objects don't fully emulate Pydantic unless configured properly
    # Actually, we can return a dictionary or a mocked Pydantic model. 
    # Since main.py returns `parsed`, which is directly passed out of the route, fastapi converts it.
    # To be safer and avoid Pydantic mock issues, we'll configure the parsed to have a model_dump method since that's what FastAPI V2 calls under the hood sometimes, 
    # OR we can just inject a real Pydantic object. Let's use the real Pydantic class to avoid serialization errors during test!
    
    from main import InterviewTurnResponse, LiveMetrics
    
    real_mock_response = InterviewTurnResponse(
        ai_feedback="Tốt lắm, bạn có giao tiếp rõ ràng.",
        next_question="Bạn có kinh nghiệm với React không?",
        metrics=LiveMetrics(
            confidence_score=95,
            confidence_feedback="Giọng nói trôi chảy, lưu loát.",
            jd_relevance_score=85,
            jd_relevance_feedback="Trả lời sát với yêu cầu JD.",
            tech_vocab_rating="TỐT"
        )
    )
    
    mock_completion = MagicMock()
    mock_completion.parsed = real_mock_response
    mock_generate_content.return_value = mock_completion

    payload = {
        "jd_text": "Tìm kiếm Frontend Dev với React và TypeScript",
        "cv_text": "Kinh nghiệm 5 năm làm React và Javascript",
        "chat_history": [
            {"role": "assistant", "content": "Bạn hãy giới thiệu bản thân nhé?"},
            {"role": "user", "content": "Mình là dev FE 5 năm kinh nghiệm."}
        ]
    }
    
    response = client.post("/api/interview/chat", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["ai_feedback"] == "Tốt lắm, bạn có giao tiếp rõ ràng."
    assert data["next_question"] == "Bạn có kinh nghiệm với React không?"
    assert data["metrics"]["confidence_score"] == 95
    assert data["metrics"]["tech_vocab_rating"] == "TỐT"
    mock_generate_content.assert_called_once()
