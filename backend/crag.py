import re
from typing import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from embedding import query_chroma
from models import Citation
from utils import compact_text, relevance_from_distance, settings

class CRAGState(TypedDict, total=False):
    question: str
    rewritten_query: str | None
    document_ids: list[str] | None
    top_k: int
    hits: list[dict]
    confidence_score: float
    corrected: bool
    answer: str
    citations: list[Citation]
    rewrite_count: int

def gemini() -> ChatGoogleGenerativeAI:
    if not settings.gemini_api_key:
        raise RuntimeError('GEMINI_API_KEY is not configured')
    return ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.gemini_api_key, temperature=0.2)

def keyword_overlap(question: str, text: str) -> float:
    q_terms = {term for term in re.findall(r'[a-zA-Z0-9]{3,}', question.lower())}
    if not q_terms:
        return 0.0
    t_terms = set(re.findall(r'[a-zA-Z0-9]{3,}', text.lower()))
    return len(q_terms & t_terms) / len(q_terms)

def grade_hits(question: str, hits: list[dict]) -> tuple[list[dict], float]:
    graded = []
    for hit in hits:
        score = (relevance_from_distance(hit.get('distance')) * 0.75) + (keyword_overlap(question, hit.get('text', '')) * 0.25)
        graded.append({**hit, 'score': round(score, 4)})
    confidence = round(sum(hit['score'] for hit in graded[:3]) / max(1, min(3, len(graded))), 4)
    return graded, confidence

async def retrieve(state: CRAGState) -> CRAGState:
    query = state.get('rewritten_query') or state['question']
    hits = await query_chroma(query, state['top_k'], state.get('document_ids'))
    graded, confidence = grade_hits(state['question'], hits)
    return {**state, 'hits': graded, 'confidence_score': confidence}

def route_after_retrieval(state: CRAGState) -> str:
    if state.get('confidence_score', 0) < settings.min_relevance_score and state.get('rewrite_count', 0) < 1:
        return 'rewrite'
    return 'generate_answer'

async def rewrite_query(state: CRAGState) -> CRAGState:
    prompt = 'Rewrite this question for precise enterprise document retrieval. Return only the rewritten query.\n\nQuestion: ' + state['question']
    response = await gemini().ainvoke(prompt)
    return {**state, 'rewritten_query': str(response.content).strip() or state['question'], 'corrected': True, 'rewrite_count': state.get('rewrite_count', 0) + 1}

def format_context(hits: list[dict]) -> str:
    blocks = []
    for index, hit in enumerate(hits, start=1):
        meta = hit['metadata']
        blocks.append(f'[{index}] Document: {meta["filename"]} | Page: {meta["page"]} | Chunk: {hit["chunk_id"]}\n{hit["text"]}')
    return '\n\n'.join(blocks)

async def generate_answer(state: CRAGState) -> CRAGState:
    hits = sorted(state.get('hits', []), key=lambda item: item.get('score', 0), reverse=True)
    context = format_context(hits)
    if not context:
        final_answer = 'I could not find relevant content in the uploaded documents for this question.'
    else:
        prompt = 'You are DocuTrust, an enterprise RAG assistant. Answer only from the provided context. If missing, say so. Use bracketed citation numbers like [1].\n\nQuestion: ' + state['question'] + '\n\nContext:\n' + context + '\n\nAnswer:'
        response = await gemini().ainvoke(prompt)
        final_answer = str(response.content).strip()
    citations = [Citation(document_id=h['metadata']['document_id'], filename=h['metadata']['filename'], page=int(h['metadata']['page']), chunk_id=h['chunk_id'], score=float(h.get('score', 0)), preview=compact_text(h['text'])) for h in hits]
    return {**state, 'answer': final_answer, 'citations': citations}

def build_crag_graph():
    graph = StateGraph(CRAGState)
    graph.add_node('retrieve', retrieve)
    graph.add_node('rewrite', rewrite_query)
    graph.add_node('generate_answer', generate_answer)
    graph.set_entry_point('retrieve')
    graph.add_conditional_edges('retrieve', route_after_retrieval, {'rewrite': 'rewrite', 'generate_answer': 'generate_answer'})
    graph.add_edge('rewrite', 'retrieve')
    graph.add_edge('generate_answer', END)
    return graph.compile()

async def run_crag(question: str, top_k: int, document_ids: list[str] | None = None) -> CRAGState:
    return await build_crag_graph().ainvoke({'question': question, 'top_k': top_k, 'document_ids': document_ids, 'rewritten_query': None, 'corrected': False, 'rewrite_count': 0})
