"""Knowledge-base ingestion: read markdown docs with YAML-style front matter,
token-aware chunk them, embed with Voyage, and upsert into KnowledgeChunk.

Usage:
    python -m ingest ../../knowledge-base --org <org-uuid>
"""

import argparse
import asyncio
import glob
import os
import re

import voyageai

from db import init_pool, close_pool, tenant_conn

_vo = voyageai.Client(api_key=os.environ.get("VOYAGE_API_KEY"))
EMBED_MODEL = "voyage-3"

FRONT_MATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_doc(text: str) -> tuple[dict, str]:
    """Split front matter (title, tags) from the markdown body."""
    meta: dict = {"title": "Untitled", "tags": []}
    m = FRONT_MATTER.match(text)
    body = text
    if m:
        for line in m.group(1).splitlines():
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if key == "tags":
                meta["tags"] = [
                    t.strip().strip('"') for t in val.strip("[]").split(",") if t.strip()
                ]
            else:
                meta[key] = val.strip('"')
        body = text[m.end():]
    return meta, body


def approx_tokens(s: str) -> int:
    # cheap heuristic: ~4 chars/token; replace with tiktoken for precision
    return max(1, len(s) // 4)


def chunk(text: str, target: int = 400, max_carry: int = 1) -> list[str]:
    paras = [p for p in text.split("\n\n") if p.strip()]
    out, buf = [], []
    for p in paras:
        buf.append(p)
        if approx_tokens("\n\n".join(buf)) >= target:
            out.append("\n\n".join(buf))
            buf = buf[-max_carry:]  # overlap for context continuity
    if buf:
        out.append("\n\n".join(buf))
    return out


async def ingest_file(path: str, org_id: str) -> int:
    with open(path, encoding="utf-8") as fh:
        meta, body = parse_doc(fh.read())
    chunks = chunk(body)
    if not chunks:
        return 0
    embs = _vo.embed(chunks, model=EMBED_MODEL, input_type="document").embeddings

    async with tenant_conn(org_id) as conn:
        doc_id = await conn.fetchval(
            """
            INSERT INTO "KnowledgeDocument" (id,"orgId",title,source,tags,"createdAt")
            VALUES (gen_random_uuid(),$1,$2,$3,$4,now())
            RETURNING id
            """,
            org_id, meta["title"], os.path.basename(path), meta["tags"],
        )
        for content, emb in zip(chunks, embs):
            emb_literal = "[" + ",".join(str(x) for x in emb) + "]"
            await conn.execute(
                """
                INSERT INTO "KnowledgeChunk"
                  (id,"documentId","orgId",content,"tokenCount",embedding,tags)
                VALUES (gen_random_uuid(),$1,$2,$3,$4,$5::vector,$6)
                """,
                doc_id, org_id, content, approx_tokens(content), emb_literal,
                meta["tags"],
            )
    return len(chunks)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="directory of .md knowledge docs")
    ap.add_argument("--org", required=True, help="organization uuid")
    args = ap.parse_args()

    await init_pool()
    try:
        files = sorted(glob.glob(os.path.join(args.path, "**/*.md"), recursive=True))
        total = 0
        for f in files:
            n = await ingest_file(f, args.org)
            total += n
            print(f"  ingested {n:>3} chunks  {os.path.relpath(f, args.path)}")
        print(f"done: {len(files)} docs, {total} chunks")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
