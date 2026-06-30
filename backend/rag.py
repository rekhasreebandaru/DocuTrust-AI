import time

from crag import run_crag
from database import get_database
from models import ChatResponse, ConfidenceBreakdown
from utils import now_utc

def estimate_tokens(text: str) -> int:
    return max(1, round(len(text.split()) * 1.33))

async def answer_question(question: str, top_k: int, document_ids: list[str] | None = None) -> ChatResponse:
    started = time.perf_counter()
    state = await run_crag(question, top_k, document_ids)
    created_at = now_utc()
    generation_time_ms = int((time.perf_counter() - started) * 1000)
    answer = state.get('answer', '')
    hits = state.get('hits', [])
    retriever_score = float(state.get('confidence_score', 0))
    citation_count = len(state.get('citations', []))
    context_coverage = min(1.0, citation_count / max(1, top_k))
    llm_confidence = min(1.0, (retriever_score * 0.7) + (context_coverage * 0.3))
    hallucination_risk = round(max(0.0, 1.0 - llm_confidence), 4)
    confidence = ConfidenceBreakdown(
        overall=round(llm_confidence, 4),
        retriever_score=round(retriever_score, 4),
        llm_confidence=round(llm_confidence, 4),
        context_coverage=round(context_coverage, 4),
        hallucination_risk=hallucination_risk,
    )
    record = {
        'title': question[:80],
        'question': question,
        'answer': answer,
        'citations': [citation.model_dump() for citation in state.get('citations', [])],
        'confidence_score': confidence.overall,
        'confidence': confidence.model_dump(),
        'corrected': bool(state.get('corrected', False)),
        'rewritten_query': state.get('rewritten_query'),
        'token_count': estimate_tokens(question + ' ' + answer),
        'generation_time_ms': generation_time_ms,
        'retrieved_documents': [{'chunk_id': hit.get('chunk_id'), 'metadata': hit.get('metadata'), 'score': hit.get('score', 0)} for hit in hits],
        'created_at': created_at,
    }
    result = await get_database().chat_history.insert_one(record)
    response_payload = {key: value for key, value in record.items() if key not in {'retrieved_documents', 'title'}}
    return ChatResponse(id=str(result.inserted_id), **response_payload)
