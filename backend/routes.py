from collections import defaultdict
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from database import get_database
from embedding import add_chunks_to_chroma, delete_document_vectors
from models import (
    ApiMessage,
    ChatHistoryItem,
    ChatRequest,
    ChatResponse,
    DashboardStats,
    DocumentMetadata,
    FeedbackRequest,
    LoginRequest,
    LoginResponse,
    RenameRequest,
    SearchResult,
    UserSettings,
)
from pdf_loader import extract_pdf_chunks
from rag import answer_question
from utils import compact_text, create_access_token, decode_access_token, make_stored_filename, now_utc, settings, validate_pdf_upload

router = APIRouter(prefix='/api')
security = HTTPBearer()

async def require_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    return decode_access_token(credentials.credentials)

def oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid id') from exc

def row_id(row: dict[str, Any]) -> str:
    return str(row.get('_id') or row.get('id'))

def date_key(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).date().isoformat()
    except Exception:
        return str(now_utc().date())

async def collect(cursor) -> list[dict[str, Any]]:
    rows = []
    async for row in cursor:
        rows.append(row)
    return rows

async def get_document_row(document_id: str) -> dict[str, Any]:
    row = await get_database().documents.find_one({'_id': oid(document_id)})
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Document not found')
    return row

@router.get('/health', response_model=ApiMessage)
async def health() -> ApiMessage:
    return ApiMessage(message='DocuTrust API is running')

@router.post('/auth/login', response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    if payload.username != settings.local_auth_username or payload.password != settings.local_auth_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid username or password')
    return LoginResponse(access_token=create_access_token(payload.username), username=payload.username)

@router.get('/dashboard/stats', response_model=DashboardStats)
async def dashboard_stats(_: str = Depends(require_user)) -> DashboardStats:
    db = get_database()
    documents = await collect(db.documents.find())
    history = await collect(db.chat_history.find())
    storage_used = sum(int(doc.get('size_bytes', 0)) for doc in documents)
    indexed_chunks = sum(int(doc.get('chunk_count', 0)) for doc in documents)

    docs_by_day: dict[str, int] = defaultdict(int)
    storage_by_day: dict[str, int] = defaultdict(int)
    questions_by_day: dict[str, int] = defaultdict(int)
    confidence_by_day: dict[str, list[float]] = defaultdict(list)

    for doc in documents:
        key = date_key(doc.get('created_at'))
        docs_by_day[key] += 1
        storage_by_day[key] += int(doc.get('size_bytes', 0))
    for chat in history:
        key = date_key(chat.get('created_at'))
        questions_by_day[key] += 1
        confidence_by_day[key].append(float(chat.get('confidence_score', 0)))

    all_days = sorted(set(docs_by_day) | set(questions_by_day) | set(storage_by_day) | set(confidence_by_day))
    confidence_trend = [{'date': day, 'value': round(sum(confidence_by_day[day]) / max(1, len(confidence_by_day[day])), 3)} for day in all_days]
    daily_activity = [{'date': day, 'uploads': docs_by_day[day], 'questions': questions_by_day[day]} for day in all_days]

    return DashboardStats(
        total_documents=len(documents),
        indexed_chunks=indexed_chunks,
        total_questions=len(history),
        storage_used_bytes=storage_used,
        embedding_model=settings.embedding_model,
        llm_model=settings.gemini_model,
        questions_by_day=[{'date': day, 'value': questions_by_day[day]} for day in all_days],
        documents_by_day=[{'date': day, 'value': docs_by_day[day]} for day in all_days],
        storage_by_day=[{'date': day, 'value': storage_by_day[day]} for day in all_days],
        confidence_trend=confidence_trend,
        daily_activity=daily_activity,
    )

@router.post('/documents/upload', response_model=list[DocumentMetadata])
async def upload_documents(files: list[UploadFile] = File(...), _: str = Depends(require_user)) -> list[DocumentMetadata]:
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Upload at least one PDF')
    db = get_database()
    uploaded: list[DocumentMetadata] = []
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    for file in files:
        validate_pdf_upload(file)
        content = await file.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'{file.filename} is empty')
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'{file.filename} is larger than 50 MB')
        stored_filename = make_stored_filename(file.filename or 'document.pdf')
        target_path = Path(settings.upload_dir) / stored_filename
        target_path.write_bytes(content)
        page_count, raw_chunks = await extract_pdf_chunks(target_path)
        if not raw_chunks:
            target_path.unlink(missing_ok=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'{file.filename} has no extractable text')
        record = {'filename': file.filename, 'stored_filename': stored_filename, 'content_type': file.content_type or 'application/pdf', 'size_bytes': len(content), 'page_count': page_count, 'chunk_count': len(raw_chunks), 'created_at': now_utc(), 'updated_at': now_utc()}
        result = await db.documents.insert_one(record)
        document_id = str(result.inserted_id)
        chunks = [{'chunk_id': f'{document_id}:{index}', 'document_id': document_id, 'filename': file.filename, 'page': chunk['page'], 'text': chunk['text']} for index, chunk in enumerate(raw_chunks)]
        await add_chunks_to_chroma(chunks)
        await db.chunks.insert_many(chunks)
        uploaded.append(DocumentMetadata(id=document_id, **record))
    return uploaded

@router.get('/documents', response_model=list[DocumentMetadata])
async def list_documents(_: str = Depends(require_user)) -> list[DocumentMetadata]:
    rows = get_database().documents.find().sort('created_at', -1)
    documents: list[DocumentMetadata] = []
    async for row in rows:
        row['id'] = row_id(row)
        row.pop('_id', None)
        documents.append(DocumentMetadata(**row))
    return documents

@router.get('/documents/{document_id}/file')
async def download_document(document_id: str, _: str = Depends(require_user)) -> FileResponse:
    row = await get_document_row(document_id)
    path = Path(settings.upload_dir) / row['stored_filename']
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Uploaded file is missing')
    return FileResponse(path, media_type='application/pdf', filename=row['filename'])

@router.patch('/documents/{document_id}/rename', response_model=ApiMessage)
async def rename_document(document_id: str, payload: RenameRequest, _: str = Depends(require_user)) -> ApiMessage:
    db = get_database()
    await get_document_row(document_id)
    await db.documents.update_one({'_id': oid(document_id)}, {'$set': {'filename': payload.name, 'updated_at': now_utc()}})
    if hasattr(db.chunks, 'update_many'):
        await db.chunks.update_many({'document_id': document_id}, {'$set': {'filename': payload.name}})
    else:
        await db.chunks.update_many({'document_id': document_id}, {'$set': {'filename': payload.name}})
    return ApiMessage(message='Document renamed')

@router.post('/documents/{document_id}/reindex', response_model=DocumentMetadata)
async def reindex_document(document_id: str, _: str = Depends(require_user)) -> DocumentMetadata:
    db = get_database()
    row = await get_document_row(document_id)
    path = Path(settings.upload_dir) / row['stored_filename']
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Uploaded file is missing')
    page_count, raw_chunks = await extract_pdf_chunks(path)
    if not raw_chunks:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Document has no extractable text')
    await delete_document_vectors(document_id)
    await db.chunks.delete_many({'document_id': document_id})
    chunks = [{'chunk_id': f'{document_id}:{index}', 'document_id': document_id, 'filename': row['filename'], 'page': chunk['page'], 'text': chunk['text']} for index, chunk in enumerate(raw_chunks)]
    await add_chunks_to_chroma(chunks)
    await db.chunks.insert_many(chunks)
    await db.documents.update_one({'_id': oid(document_id)}, {'$set': {'page_count': page_count, 'chunk_count': len(chunks), 'updated_at': now_utc()}})
    row.update({'id': document_id, 'page_count': page_count, 'chunk_count': len(chunks)})
    row.pop('_id', None)
    return DocumentMetadata(**row)

@router.delete('/documents/{document_id}', response_model=ApiMessage)
async def delete_document(document_id: str, _: str = Depends(require_user)) -> ApiMessage:
    db = get_database()
    row = await get_document_row(document_id)
    await delete_document_vectors(document_id)
    await db.chunks.delete_many({'document_id': document_id})
    await db.documents.delete_one({'_id': oid(document_id)})
    (Path(settings.upload_dir) / row['stored_filename']).unlink(missing_ok=True)
    return ApiMessage(message='Document deleted')

@router.get('/search', response_model=list[SearchResult])
async def global_search(q: str = Query(min_length=2), _: str = Depends(require_user)) -> list[SearchResult]:
    query = q.lower()
    chunks = await collect(get_database().chunks.find())
    results: list[SearchResult] = []
    for chunk in chunks:
        text = str(chunk.get('text', ''))
        if query in text.lower() or any(term in text.lower() for term in query.split()):
            score = min(1.0, max(0.25, text.lower().count(query) / 5 if query in text.lower() else 0.35))
            results.append(SearchResult(document_id=chunk['document_id'], filename=chunk['filename'], page=int(chunk['page']), chunk_id=chunk['chunk_id'], score=round(score, 3), preview=compact_text(text, 520)))
    return results[:25]

@router.post('/chat/query', response_model=ChatResponse)
async def chat(payload: ChatRequest, _: str = Depends(require_user)) -> ChatResponse:
    try:
        return await answer_question(payload.question, payload.top_k or settings.top_k, payload.document_ids)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

@router.get('/chat/history', response_model=list[ChatHistoryItem])
async def chat_history(_: str = Depends(require_user)) -> list[ChatHistoryItem]:
    rows = get_database().chat_history.find().sort('created_at', -1).limit(200)
    history: list[ChatHistoryItem] = []
    async for row in rows:
        row['id'] = row_id(row)
        row.pop('_id', None)
        history.append(ChatHistoryItem(**row))
    return history

@router.get('/chat/{chat_id}', response_model=ChatHistoryItem)
async def get_chat(chat_id: str, _: str = Depends(require_user)) -> ChatHistoryItem:
    row = await get_database().chat_history.find_one({'_id': oid(chat_id)})
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Chat not found')
    row['id'] = row_id(row)
    row.pop('_id', None)
    return ChatHistoryItem(**row)

@router.patch('/chat/{chat_id}/rename', response_model=ApiMessage)
async def rename_chat(chat_id: str, payload: RenameRequest, _: str = Depends(require_user)) -> ApiMessage:
    await get_database().chat_history.update_one({'_id': oid(chat_id)}, {'$set': {'title': payload.name, 'updated_at': now_utc()}})
    return ApiMessage(message='Chat renamed')

@router.delete('/chat/{chat_id}', response_model=ApiMessage)
async def delete_chat(chat_id: str, _: str = Depends(require_user)) -> ApiMessage:
    await get_database().chat_history.delete_one({'_id': oid(chat_id)})
    return ApiMessage(message='Chat deleted')

@router.post('/chat/{chat_id}/feedback', response_model=ApiMessage)
async def save_feedback(chat_id: str, payload: FeedbackRequest, _: str = Depends(require_user)) -> ApiMessage:
    db = get_database()
    await db.feedback.update_one({'chat_id': chat_id}, {'$set': {'chat_id': chat_id, 'feedback': payload.feedback, 'created_at': now_utc()}}, upsert=True)
    await db.chat_history.update_one({'_id': oid(chat_id)}, {'$set': {'feedback': payload.feedback}})
    return ApiMessage(message='Feedback saved')

def chat_export_text(row: dict[str, Any], fmt: str) -> str:
    citations = row.get('citations', [])
    if fmt == 'markdown':
        source_lines = '\n'.join(f"- {c.get('filename')} page {c.get('page')} score {round(float(c.get('score', 0))*100)}%" for c in citations)
        return f"# DocuTrust Chat Export\n\n## Question\n{row.get('question', '')}\n\n## Answer\n{row.get('answer', '')}\n\n## Sources\n{source_lines}\n"
    if fmt == 'word':
        source_items = ''.join(f"<li>{c.get('filename')} page {c.get('page')}</li>" for c in citations)
        return f"<html><body><h1>DocuTrust Chat Export</h1><h2>Question</h2><p>{row.get('question', '')}</p><h2>Answer</h2><p>{row.get('answer', '')}</p><h2>Sources</h2><ul>{source_items}</ul></body></html>"
    source_text = '; '.join(f"{c.get('filename')} p.{c.get('page')}" for c in citations)
    return f"Question:\n{row.get('question', '')}\n\nAnswer:\n{row.get('answer', '')}\n\nSources:\n{source_text}\n"

@router.get('/chat/{chat_id}/export/{fmt}')
async def export_chat(chat_id: str, fmt: str, _: str = Depends(require_user)):
    row = await get_database().chat_history.find_one({'_id': oid(chat_id)})
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Chat not found')
    if fmt == 'pdf':
        buffer = BytesIO(); pdf = canvas.Canvas(buffer, pagesize=letter); width, height = letter; y = height - 48
        def write_wrapped(label: str, text: str) -> None:
            nonlocal y
            pdf.setFont('Helvetica-Bold', 11); pdf.drawString(48, y, label); y -= 18; pdf.setFont('Helvetica', 10)
            for start in range(0, len(text), 95):
                if y < 70:
                    pdf.showPage(); y = height - 48; pdf.setFont('Helvetica', 10)
                pdf.drawString(48, y, text[start:start + 95]); y -= 14
            y -= 10
        write_wrapped('Question', row.get('question', '')); write_wrapped('Answer', row.get('answer', ''))
        write_wrapped('Citations', '; '.join(f"{c.get('filename')} p.{c.get('page')}" for c in row.get('citations', [])))
        pdf.save(); buffer.seek(0)
        return StreamingResponse(buffer, media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename=docutrust-chat-{chat_id}.pdf'})
    if fmt not in {'markdown', 'text', 'word'}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unsupported export format')
    text = chat_export_text(row, fmt)
    media = 'text/markdown' if fmt == 'markdown' else 'application/msword' if fmt == 'word' else 'text/plain'
    ext = 'md' if fmt == 'markdown' else 'doc' if fmt == 'word' else 'txt'
    return PlainTextResponse(text, media_type=media, headers={'Content-Disposition': f'attachment; filename=docutrust-chat-{chat_id}.{ext}'})

@router.get('/chat/{chat_id}/pdf')
async def download_chat_pdf(chat_id: str, _: str = Depends(require_user)):
    return await export_chat(chat_id, 'pdf', _)

@router.get('/settings', response_model=UserSettings)
async def get_settings(_: str = Depends(require_user)) -> UserSettings:
    row = await get_database().settings.find_one({'scope': 'global'})
    if not row:
        return UserSettings(embedding_model=settings.embedding_model, chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap, top_k=settings.top_k)
    return UserSettings(**{key: value for key, value in row.items() if key not in {'_id', 'scope'}})

@router.put('/settings', response_model=UserSettings)
async def update_settings(payload: UserSettings, _: str = Depends(require_user)) -> UserSettings:
    await get_database().settings.update_one({'scope': 'global'}, {'$set': {'scope': 'global', **payload.model_dump(), 'updated_at': now_utc()}}, upsert=True)
    return payload
