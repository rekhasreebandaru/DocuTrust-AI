# DocuTrust

DocuTrust is an enterprise-style Advanced RAG platform with automated self-correction. It allows users to upload PDF documents, index them with embeddings, ask natural-language questions, and receive answers with citations, confidence metrics, and chat history.

## Features

- Simple admin login and session persistence
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

## Project Structure

```text
DocuTrust/
├── backend/
│   ├── app.py
│   ├── routes.py
│   ├── database.py
│   ├── rag.py
│   ├── crag.py
│   ├── embedding.py
│   ├── pdf_loader.py
│   ├── models.py
│   ├── utils.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
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

Update `backend/.env` with your MongoDB Atlas connection string and Gemini API key before running.

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

## Default Login

```text
Username: admin
Password: admin123
```

## Security Note

Do not commit real API keys, MongoDB passwords, uploaded PDFs, ChromaDB data, local database files, virtual environments, or `node_modules`. This repository includes `.env.example` only for configuration reference.

## Demo Video

[Watch Demo Video](https://drive.google.com/file/d/1mj6uHOPx5e6ET9fO_UrdNwmRwPD3HQM9/view?usp=sharing)
