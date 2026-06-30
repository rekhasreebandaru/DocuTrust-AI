import asyncio
from functools import lru_cache
import chromadb
from chromadb.api.models.Collection import Collection
from utils import settings

@lru_cache(maxsize=1)
def get_embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model)

async def embed_texts(texts: list[str]) -> list[list[float]]:
    def work() -> list[list[float]]:
        embeddings = get_embedding_model().encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return embeddings.tolist()
    return await asyncio.to_thread(work)

async def embed_query(text: str) -> list[float]:
    return (await embed_texts([text]))[0]

@lru_cache(maxsize=1)
def get_chroma_collection() -> Collection:
    client = chromadb.PersistentClient(path=settings.chroma_dir)
    return client.get_or_create_collection(name=settings.chroma_collection, metadata={'hnsw:space': 'cosine'})

async def add_chunks_to_chroma(chunks: list[dict]) -> None:
    if not chunks:
        return
    embeddings = await embed_texts([chunk['text'] for chunk in chunks])
    await asyncio.to_thread(get_chroma_collection().upsert, ids=[chunk['chunk_id'] for chunk in chunks], embeddings=embeddings, documents=[chunk['text'] for chunk in chunks], metadatas=[{'document_id': chunk['document_id'], 'filename': chunk['filename'], 'page': chunk['page']} for chunk in chunks])

async def query_chroma(question: str, top_k: int, document_ids: list[str] | None = None) -> list[dict]:
    where = {'document_id': {'$in': document_ids}} if document_ids else None
    result = await asyncio.to_thread(get_chroma_collection().query, query_embeddings=[await embed_query(question)], n_results=top_k, where=where, include=['documents', 'metadatas', 'distances'])
    hits: list[dict] = []
    for chunk_id, text, metadata, distance in zip(result.get('ids', [[]])[0], result.get('documents', [[]])[0], result.get('metadatas', [[]])[0], result.get('distances', [[]])[0]):
        hits.append({'chunk_id': chunk_id, 'text': text, 'metadata': metadata, 'distance': distance})
    return hits

async def delete_document_vectors(document_id: str) -> None:
    await asyncio.to_thread(get_chroma_collection().delete, where={'document_id': document_id})
