from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=120)

class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal['bearer'] = 'bearer'
    username: str

class DocumentMetadata(BaseModel):
    id: str
    filename: str
    stored_filename: str
    content_type: str
    size_bytes: int
    page_count: int
    chunk_count: int
    created_at: datetime

class Citation(BaseModel):
    document_id: str
    filename: str
    page: int
    chunk_id: str
    score: float
    preview: str

class ConfidenceBreakdown(BaseModel):
    overall: float = 0
    retriever_score: float = 0
    llm_confidence: float = 0
    context_coverage: float = 0
    hallucination_risk: float = 0

class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    document_ids: list[str] | None = None

class ChatResponse(BaseModel):
    id: str
    question: str
    answer: str
    citations: list[Citation]
    confidence_score: float
    confidence: ConfidenceBreakdown = Field(default_factory=ConfidenceBreakdown)
    corrected: bool
    rewritten_query: str | None
    token_count: int = 0
    generation_time_ms: int = 0
    created_at: datetime

class ChatHistoryItem(ChatResponse):
    retrieved_documents: list[dict[str, Any]] = []
    title: str | None = None
    feedback: str | None = None

class RenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)

class FeedbackRequest(BaseModel):
    feedback: Literal['like', 'dislike']

class UserSettings(BaseModel):
    theme: Literal['light', 'dark', 'system'] = 'system'
    embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2'
    chunk_size: int = Field(default=900, ge=200, le=3000)
    chunk_overlap: int = Field(default=180, ge=0, le=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    temperature: float = Field(default=0.2, ge=0, le=1)
    max_tokens: int = Field(default=2048, ge=256, le=8192)
    language: str = 'English'

class SearchResult(BaseModel):
    document_id: str
    filename: str
    page: int
    chunk_id: str
    score: float
    preview: str

class DashboardStats(BaseModel):
    total_documents: int
    indexed_chunks: int
    total_questions: int
    storage_used_bytes: int
    embedding_model: str
    llm_model: str
    questions_by_day: list[dict[str, Any]]
    documents_by_day: list[dict[str, Any]]
    storage_by_day: list[dict[str, Any]]
    confidence_trend: list[dict[str, Any]]
    daily_activity: list[dict[str, Any]]

class ApiMessage(BaseModel):
    message: str
