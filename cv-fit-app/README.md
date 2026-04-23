# CVFit — AI Interview Prep

> Upload your CV + job description. Get a match score, a tailored resume, and a mock interview session.

## Project Structure

```
cv-fit-app/
├── frontend/          # Next.js 16 (App Router) + Tailwind CSS
│   └── src/app/
│       ├── page.tsx         → Landing page
│       ├── app/page.tsx     → Upload CV + JD
│       ├── results/page.tsx → Match score + tailored CV
│       └── interview/page.tsx → Mock interview chat
│
└── backend/           # Python FastAPI
    ├── main.py              → All API logic (single file)
    ├── requirements.txt
    └── .env.example
```

## Quick Start

### 1. Backend (FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up your OpenAI key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run the server
uvicorn main:app --reload --port 8000
```

Backend will be live at **http://localhost:8000**

### 2. Frontend (Next.js)

```bash
cd frontend

# Install dependencies (already done via create-next-app)
npm install

# Start dev server
npm run dev
```

Frontend will be live at **http://localhost:3000**

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/api/upload-and-match` | Upload PDF + JD → match score + tailored CV |
| `POST` | `/api/interview/chat` | Send chat history → AI interviewer response |

## Features

- 📊 **Match Score** — 0-100 fit score with missing skills list
- 📄 **Tailored CV** — AI rewrites your resume to match the JD; exportable as PDF via print
- 🎤 **Voice Input** — Web Speech API for Vietnamese 🇻🇳 and English 🇺🇸
- 🔊 **AI Voice** — Speech Synthesis reads interviewer questions aloud
- ☕ **Buy Me a Coffee** — Modal after 5 interview exchanges

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 16, React 19, Tailwind CSS |
| Backend | FastAPI, Pydantic, Uvicorn |
| AI | OpenAI `gpt-4o-mini` |
| PDF parsing | pdfplumber |
