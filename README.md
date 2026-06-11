# Growth Operator Platform

A multi-tenant SaaS + interactive AI learning engine that trains users as
**Growth Operators** (monetizing creator audiences, building communities, and
scaling digital info-products).

> All knowledge-base content under `knowledge-base/` is **original, synthetic
> training material** authored for this project. It is generic business and
> direct-response copywriting best practice — not extracted from, or a copy of,
> any third-party platform's proprietary content.

## Architecture

Four independently-scalable planes:

```
Client (Next.js)  ──►  Core API (NestJS + Prisma + Postgres)  ──►  AI Orchestration (FastAPI + Claude + pgvector)
                                    │                                         │
                                    ▼                                         ▼
                              Redis (cache/queue)                     Postgres + pgvector
                                    │
                                    ▼
                           CDN (R2/S3, signed URLs)
```

See [`docs/architecture.md`](docs/architecture.md) for the full design,
Redis caching strategy, and the context-injection payload format.

## Layout

| Path | What |
|---|---|
| `prisma/schema.prisma` | Multi-tenant relational + vector schema |
| `prisma/migrations/001_init_rls_pgvector.sql` | RLS policies + HNSW index |
| `services/ai/` | FastAPI AI orchestration: agent graph, RAG ingest, system prompt |
| `services/core/` | NestJS Core API skeleton (auth, LMS, chat proxy) |
| `knowledge-base/` | Seed knowledge corpus + synthetic transcripts (RAG source) |
| `docs/` | Architecture, prompts, context payload |

## Stack

- **Frontend:** Next.js 15 (App Router) + React 19 + TypeScript + Tailwind
- **Core API:** NestJS (Node 22) + Prisma
- **AI service:** FastAPI (Python 3.12) + Anthropic Claude + Voyage embeddings
- **Data:** PostgreSQL 16 + pgvector, Redis 7
- **Storage/CDN:** Cloudflare R2 + CDN (signed URLs)

## Quickstart

```bash
# 1. Database
docker compose up -d postgres redis
# 2. Schema
cd prisma && npx prisma migrate dev
psql "$DATABASE_URL" -f migrations/001_init_rls_pgvector.sql
# 3. AI service
cd services/ai && pip install -r requirements.txt && uvicorn app:app --reload
# 4. Ingest the seed knowledge base
python -m ingest ../../knowledge-base
```

Set `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `DATABASE_URL`, and `REDIS_URL`
in `.env` first (see `.env.example`).
