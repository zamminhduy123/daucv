"""Test full CV analysis end-to-end with realistic CV text"""

import asyncio
import time

from app.services import cv_analysis_service
from app.services.files import FileService

SAMPLE_CV = """
NGUYỄN VĂN A
Lập trình viên Full Stack (Senior)
Email: nguyenvana@example.com | SĐT: 0901234567 | Location: Hồ Chí Minh, Việt Nam

TỔNG QUAN
Lập trình viên Full Stack với hơn 5 năm kinh nghiệm thiết kế và phát triển hệ thống Web ứng dụng React.js, Next.js, Node.js, FastAPI và PostgreSQL.

KINH NGHIỆM LÀM VIỆC
Công ty Công nghệ ABC — Senior Full Stack Developer (01/2022 - Hiện tại)
- Thiết kế hệ thống microservices phục vụ 500,000 người dùng hàng tháng bằng FastAPI, Next.js và Supabase.
- Tối ưu hóa hiệu năng cơ sở dữ liệu PostgreSQL, giảm thời gian phản hồi API từ 450ms xuống 120ms.
- Xây dựng quy trình CI/CD với Docker và GitHub Actions.

Công ty XYZ — Frontend Developer (06/2019 - 12/2021)
- Phát triển giao diện người dùng sử dụng React.js, Redux Toolkit và Tailwind CSS.

HỌC VẤN
Đại học Bách Khoa TP.HCM — Cử nhân Khai thác dữ liệu & CNTT (2015 - 2019)

KỸ NĂNG
- Ngôn ngữ: JavaScript, TypeScript, Python, SQL
- Frameworks: React, Next.js, Node.js, FastAPI
- Databases & Tools: PostgreSQL, Docker, Git, RESTful API
"""

SAMPLE_JD = """
Vị trí: Senior Fullstack Developer (Node.js / React / Python)
Yêu cầu:
- Tối thiểu 4 năm kinh nghiệm lập trình Web.
- Thành thạo JavaScript, TypeScript, Python, React.js, Next.js.
- Có kinh nghiệm làm việc với cơ sở dữ liệu PostgreSQL, Docker, CI/CD.
- Khả năng tối ưu hiệu năng API và hệ thống có lượng truy cập lớn.
"""


async def progress_logger(stage: str, message: str, details: dict = None):
    print(f"  [STREAM PROGRESS] [{stage}]: {message} (details={details})", flush=True)


async def main():
    print("=== TESTING END-TO-END CV ANALYSIS ===", flush=True)
    t0 = time.time()
    try:
        file_service = FileService(storage=None)
        result = await cv_analysis_service.analyze_cv(
            cv_text=SAMPLE_CV,
            jd_text=SAMPLE_JD,
            user_id="test-user-123",
            file_service=file_service,
            progress=progress_logger,
        )
        dt = time.time() - t0
        print(f"\n🎉 ANALYSIS SUCCESSFUL in {dt:.2f}s!", flush=True)
        print(f"Role Fit Score: {result.role_fit_score}%")
        print(f"Match Score: {result.match_score}%")
        print(f"Headline: {result.match_headline}")
        print(f"Strengths ({len(result.cv_strengths)}): {result.cv_strengths[:2]}")
        print(
            f"Keywords to Add ({len(result.prioritized_keywords)}): {[k.keyword for k in result.prioritized_keywords[:3]]}"
        )
    except Exception as exc:
        dt = time.time() - t0
        print(
            f"\n❌ ANALYSIS FAILED in {dt:.2f}s: {type(exc).__name__}: {exc}",
            flush=True,
        )
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
