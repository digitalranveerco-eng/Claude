"""RAG retrieval: embed the query, run a tenant-scoped, tag-filtered ANN search,
optionally fuse with full-text (BM25-style) results, and rerank.

Embeddings use Voyage AI (`voyage-3`, 1024 dims) - Anthropic's recommended
embedding partner, since Claude has no native embeddings API.
"""

import hashlib
import json
import os

import voyageai

from db import tenant_conn

_vo = voyageai.Client(api_key=os.environ.get("VOYAGE_API_KEY"))
EMBED_MODEL = "voyage-3"
RERANK_MODEL = "rerank-2"


def cache_key(section_id: str, query: str) -> str:
    norm = " ".join(query.lower().split())
    return "rag:" + hashlib.sha256(f"{section_id}|{norm}".encode()).hexdigest()


async def retrieve(
    org_id: str,
    query: str,
    allowed_tags: list[str],
    top_k: int = 6,
    candidate_k: int = 20,
) -> list[str]:
    """Return the top_k most relevant chunk contents for the query."""
    q_emb = _vo.embed([query], model=EMBED_MODEL, input_type="query").embeddings[0]
    emb_literal = "[" + ",".join(str(x) for x in q_emb) + "]"

    async with tenant_conn(org_id) as conn:
        # Vector ANN candidates (RLS already scopes to org).
        ann = await conn.fetch(
            """
            SELECT content, tags, embedding <=> $1::vector AS dist
            FROM "KnowledgeChunk"
            WHERE ($2::text[] = '{}' OR tags && $2::text[])
            ORDER BY embedding <=> $1::vector
            LIMIT $3
            """,
            emb_literal,
            allowed_tags,
            candidate_k,
        )
        # Full-text candidates fused in (hybrid retrieval).
        fts = await conn.fetch(
            """
            SELECT content, tags
            FROM "KnowledgeChunk"
            WHERE content_tsv @@ plainto_tsquery('english', $1)
              AND ($2::text[] = '{}' OR tags && $2::text[])
            LIMIT $3
            """,
            query,
            allowed_tags,
            candidate_k,
        )

    # Reciprocal-rank fusion of the two candidate lists.
    fused: dict[str, float] = {}
    for rank, row in enumerate(ann):
        fused[row["content"]] = fused.get(row["content"], 0) + 1 / (rank + 60)
    for rank, row in enumerate(fts):
        fused[row["content"]] = fused.get(row["content"], 0) + 1 / (rank + 60)
    candidates = [c for c, _ in sorted(fused.items(), key=lambda kv: -kv[1])]
    candidates = candidates[:candidate_k]
    if not candidates:
        return []

    # Rerank for precision, keep the best top_k.
    reranked = _vo.rerank(query, candidates, model=RERANK_MODEL, top_k=top_k)
    return [r.document for r in reranked.results]
