import asyncio
import re
from pathlib import Path
from pypdf import PdfReader
from utils import settings

def _normalize_pdf_text(text: str) -> str:
    text = text.replace('\x00', ' ')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def _split_text(page_text: str, page_number: int) -> list[dict]:
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', page_text) if p.strip()]
    chunks: list[dict] = []
    current = ''
    for paragraph in paragraphs:
        candidate = f'{current}\n\n{paragraph}'.strip() if current else paragraph
        if len(candidate) <= settings.chunk_size:
            current = candidate
            continue
        if current:
            chunks.append({'page': page_number, 'text': current})
        current = paragraph
        while len(current) > settings.chunk_size:
            chunks.append({'page': page_number, 'text': current[:settings.chunk_size].strip()})
            current = current[max(0, settings.chunk_size - settings.chunk_overlap):].strip()
    if current:
        chunks.append({'page': page_number, 'text': current})
    return chunks

def _extract_pdf_sync(path: Path) -> tuple[int, list[dict]]:
    reader = PdfReader(str(path))
    chunks: list[dict] = []
    for index, page in enumerate(reader.pages, start=1):
        text = _normalize_pdf_text(page.extract_text() or '')
        if text:
            chunks.extend(_split_text(text, index))
    return len(reader.pages), chunks

async def extract_pdf_chunks(path: Path) -> tuple[int, list[dict]]:
    return await asyncio.to_thread(_extract_pdf_sync, path)
