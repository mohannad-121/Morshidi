# Morshidi

Morshidi is an academic intelligence project for trusted study-decision support.

## Current architecture

- `apps/web` — Next.js + TypeScript frontend
- `apps/api` — FastAPI + Python backend
- `academic-data` — verified academic source datasets
- `docs` — architecture and validation documents
- `supabase` — reserved for future database infrastructure

## Backend local setup

```powershell
cd apps/api
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Frontend local setup

```powershell
cd apps/web
npm install
npm run dev
```

## Local URLs

- Frontend: http://localhost:3000
- Backend: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

Database infrastructure, Rules Engine, student data, recommendations, and AI are not implemented yet.
