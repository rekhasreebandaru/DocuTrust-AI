# DocuTrust

DocuTrust is an enterprise-style Advanced RAG platform with automated self-correction. It allows users to upload PDF documents, index them with embeddings, ask natural-language questions, and receive answers with citations, confidence metrics, and chat history.

> **This is a fork.** The original DocuTrust project was built by [**rekhasreebandaru**](https://github.com/rekhasreebandaru/DocuTrust-AI). This fork keeps the original RAG/CRAG pipeline, ingestion flow, and UI intact and adds the features listed below under **What's new in this fork**. All credit for the core architecture (FastAPI + React + ChromaDB + MongoDB Atlas + Gemini, corrective RAG loop, citation/confidence scoring) belongs to the original author.

## What's new in this fork

Added by **Yuvrajjit Baruah** ([@yuvrajjitbaruah](https://github.com/yuvrajjitbaruah)) on top of the original codebase:

| Feature | What it does | Key files touched |
|---|---|---|
| **Multi-user auth** | Real registration + bcrypt password hashing + role-based JWTs (`admin`/`user`), replacing the single hardcoded `admin/admin123` login. First registered account becomes admin. Legacy demo login still works. | `backend/utils.py`, `backend/models.py`, `backend/routes.py`, `frontend/src/pages/Register.tsx`, `frontend/src/hooks/useAuth.tsx` |
| **Document tags & folders** | Organize uploaded PDFs with custom tags and a folder label; filter the document list by either. | `backend/models.py`, `backend/routes.py`, `frontend/src/pages/Upload.tsx` |
| **Pin conversations** | Pin important chat threads so they always sort to the top of History. | `backend/routes.py`, `frontend/src/pages/History.tsx` |
| **Public share links** | Generate a read-only, no-login link for a single chat answer + citations, for sharing outside the app. | `backend/routes.py`, `frontend/src/pages/SharedChat.tsx` |
| **Audit log** | Every login, upload, delete, rename, query, feedback, and share action is recorded with user + timestamp. Admin-only view in the UI. | `backend/database.py`, `backend/routes.py`, `frontend/src/pages/AuditLog.tsx` |
| **API rate limiting** | In-memory sliding-window limiter (configurable requests/window) on all `/api` routes to blunt abuse. | `backend/utils.py`, `backend/app.py` |

See the [Wiki](./wiki) for a deeper write-up of each feature, including new API endpoints and env vars.

## Features (original)

- Multi-PDF upload with local file storage
- PDF text extraction using PyPDF
- Semantic chunking and Sentence Transformers embeddings
- ChromaDB vector search
- MongoDB Atlas metadata and chat storage, with local fallback for development
- Google Gemini answer generation
- Corrective RAG flow with retrieval scoring and query retry logic
- Source citations with page number and similarity score
- Dashboard analytics, document library, settings, history, and exports
- Responsive React + Tailwind enterprise UI with dark mode

## Tech Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, Axios
- Backend: FastAPI, Python
- Database: MongoDB Atlas
- Vector Database: ChromaDB
- AI: Google Gemini API
- Embeddings: Sentence Transformers
- PDF Processing: PyPDF
- Auth: python-jose (JWT) + passlib/bcrypt *(new)*

## Project Structure

```text
DocuTrust/
├── backend/
│   ├── app.py            # FastAPI app, CORS, rate-limit middleware
│   ├── routes.py         # All API routes (auth, documents, chat, audit, share)
│   ├── database.py       # MongoDB Atlas client + local JSON fallback
│   ├── rag.py
│   ├── crag.py
│   ├── embedding.py
│   ├── pdf_loader.py
│   ├── models.py         # Pydantic request/response models
│   ├── utils.py          # Settings, JWT, password hashing, rate limiter
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/         # Includes new Register, AuditLog, SharedChat
│   │   ├── components/
│   │   ├── hooks/
│   │   └── services/
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── wiki/                  # Wiki pages (mirror these into the GitHub Wiki tab)
├── README.md
└── .gitignore
```

## Backend Setup

```powershell
cd backend
python -m venv .venv
..venvScriptsactivate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Update `backend/.env` with your MongoDB Atlas connection string and Gemini API key before running. See [`wiki/Configuration.md`](./wiki/Configuration.md) for the full list of environment variables, including the new auth/rate-limit settings.

## Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

Frontend runs on:

```text
http://localhost:5173
```

Backend runs on:

```text
http://localhost:8000
```

## Login

Two ways in:

- **Register a new account** at `/register` — the first account created becomes an admin.
- **Legacy demo login** (kept for backwards compatibility):

```text
Username: admin
Password: admin123
```

## Security Note

Do not commit real API keys, MongoDB passwords, uploaded PDFs, ChromaDB data, local database files, virtual environments, or `node_modules`. This repository includes `.env.example` only for configuration reference. Rotate `JWT_SECRET` before deploying anywhere beyond localhost.


## Attribution

- Original project & core RAG/CRAG architecture: [rekhasreebandaru/DocuTrust-AI](https://github.com/rekhasreebandaru/DocuTrust-AI)
- Fork maintained by: [Yuvrajjit Baruah](https://github.com/yuvrajjitbaruah)

No LICENSE file was published upstream at the time of this fork — check the original repository for the current license status before redistributing.
