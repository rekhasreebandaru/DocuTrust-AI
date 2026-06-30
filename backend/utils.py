import hashlib
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from fastapi import HTTPException, UploadFile, status
from jose import JWTError, jwt
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = 'DocuTrust'
    environment: str = 'development'
    api_host: str = '0.0.0.0'
    api_port: int = 8000
    frontend_origin: str = 'http://localhost:5173'
    local_auth_username: str = 'admin'
    local_auth_password: str = 'admin123'
    jwt_secret: str = 'change-this-development-secret'
    mongodb_uri: str
    mongodb_db: str = 'docutrust'
    gemini_api_key: str = ''
    gemini_model: str = 'gemini-1.5-flash'
    embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2'
    upload_dir: str = 'uploads'
    chroma_dir: str = 'chroma_store'
    chroma_collection: str = 'docutrust_chunks'
    chunk_size: int = 900
    chunk_overlap: int = 180
    top_k: int = 5
    min_relevance_score: float = 0.42
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

settings = Settings()
ALGORITHM = 'HS256'

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def ensure_runtime_dirs() -> None:
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_dir).mkdir(parents=True, exist_ok=True)

def create_access_token(subject: str, expires_minutes: int = 480) -> str:
    payload: dict[str, Any] = {'sub': subject, 'exp': now_utc() + timedelta(minutes=expires_minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)

def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        subject = payload.get('sub')
        if not subject:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')
        return str(subject)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token') from exc

def make_stored_filename(original_name: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9._-]+', '_', Path(original_name).name).strip('._') or 'document.pdf'
    stem = Path(cleaned).stem[:80]
    digest = hashlib.sha256(f'{original_name}-{time.time_ns()}'.encode()).hexdigest()[:12]
    return f'{stem}_{digest}.pdf'

def validate_pdf_upload(file: UploadFile) -> None:
    filename = file.filename or ''
    if not filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'{filename} is not a PDF')
    if file.content_type and file.content_type not in {'application/pdf', 'application/octet-stream'}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'{filename} has invalid content type')

def relevance_from_distance(distance: float | None) -> float:
    return 0.0 if distance is None else max(0.0, min(1.0, 1.0 / (1.0 + float(distance))))

def compact_text(text: str, limit: int = 420) -> str:
    normalized = re.sub(r'\s+', ' ', text).strip()
    return normalized if len(normalized) <= limit else normalized[:limit - 3].rstrip() + '...'
