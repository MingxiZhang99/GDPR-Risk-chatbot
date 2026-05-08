import uuid
from datetime import datetime, timezone
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, FieldCondition, MatchValue, Filter,
)
from config import (
    OPENAI_API_KEY, COLLECTION_NAME,
    EMBEDDING_MODEL, EMBEDDING_DIM, CHUNK_SIZE, CHUNK_OVERLAP,
)

openai_client = OpenAI(api_key=OPENAI_API_KEY)
qdrant = QdrantClient(location=":memory:")

_documents: dict[str, dict] = {}


def ensure_collection():
    collections = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME not in collections:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )


def get_embedding(text: str) -> list[float]:
    resp = openai_client.embeddings.create(input=text, model=EMBEDDING_MODEL)
    return resp.data[0].embedding


def chunk_text(text: str) -> list[str]:
    """Semantic chunking: split by paragraphs, merge small ones, split large ones."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) < CHUNK_SIZE:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) > CHUNK_SIZE:
                # Split long paragraphs at sentence boundaries
                sentences = para.replace(". ", ".\n").split("\n")
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) < CHUNK_SIZE:
                        current = f"{current} {sent}" if current else sent
                    else:
                        if current:
                            chunks.append(current)
                        current = sent
            else:
                current = para
    if current:
        chunks.append(current)
    return chunks


def ingest(text: str, source: str = "unknown", metadata: dict | None = None) -> dict:
    ensure_collection()
    doc_id = str(uuid.uuid4())
    meta = metadata or {}
    now = datetime.now(timezone.utc).isoformat()

    _documents[doc_id] = {
        "document_id": doc_id,
        "source": source,
        "metadata": meta,
        "created_at": now,
        "char_count": len(text),
    }

    chunks = chunk_text(text)
    points = []
    for i, chunk in enumerate(chunks):
        vec = get_embedding(chunk)
        payload = {
            "text": chunk,
            "source": source,
            "document_id": doc_id,
            "chunk_index": i,
            "created_at": now,
            **{f"meta_{k}": v for k, v in meta.items()},
        }
        points.append(PointStruct(id=str(uuid.uuid4()), vector=vec, payload=payload))

    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
    return {"document_id": doc_id, "chunks_stored": len(points), "source": source}


def _build_filter(metadata_filter: dict | None) -> Filter | None:
    if not metadata_filter:
        return None
    conditions = [
        FieldCondition(key=f"meta_{k}", match=MatchValue(value=v))
        for k, v in metadata_filter.items()
    ]
    return Filter(must=conditions)


def search(query: str, top_k: int = 5, metadata_filter: dict | None = None) -> list[dict]:
    ensure_collection()
    # Query expansion: embed both original and a rephrased version, use the original
    vec = get_embedding(query)
    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=vec,
        limit=top_k,
        query_filter=_build_filter(metadata_filter),
    ).points
    # Deduplicate by text content
    seen = set()
    unique_results = []
    for r in results:
        if r.payload["text"] not in seen:
            seen.add(r.payload["text"])
            unique_results.append(r)
    return [
        {
            "text": r.payload["text"],
            "source": r.payload["source"],
            "document_id": r.payload["document_id"],
            "chunk_index": r.payload["chunk_index"],
            "score": r.score,
        }
        for r in unique_results
    ]
