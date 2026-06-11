# Architecture

Four independently-scalable planes: **Client**, **Core API**, **AI
Orchestration**, **Content Delivery**.

```
Client (Next.js)
  │ HTTPS / WSS
  ▼
Core API (NestJS + Prisma)  ──signed URLs──►  CDN (R2/S3)
  │                  │
  │ async (BullMQ)   │ HTTP/gRPC
  ▼                  ▼
Redis            AI Orchestration (FastAPI + Claude + Voyage)
                       │
                       ▼
                 PostgreSQL + pgvector
```

## Request flow (interactive skill session)

1. User opens `/dashboard/skills/[skillId]?section=<uuid>`. The Next.js Server
   Component reads the param, fetches static content + progress from the Core API.
2. A chat message opens a WebSocket / streaming `fetch` to the Core API, which
   proxies to the AI Orchestration layer.
3. Orchestrator: resolve tenant + agent config → RAG retrieval (pgvector) →
   assemble messages → stream tokens from Claude → persist turn + token usage.
4. Media is served directly from the CDN via signed, expiring URLs — bytes never
   pass through the API.

## Redis caching strategy

| Key pattern | Holds | TTL | Invalidated by |
|---|---|---|---|
| `sess:{userId}` | session: orgId, role, current sectionId | 30 min sliding | logout, role change |
| `section:{sectionId}` | rendered lesson metadata + body hash | 1 h | section edit (pub/sub bust) |
| `progress:{userId}:{courseId}` | per-section status map | 10 min | write-through on update |
| `agentctx:{sectionId}` | system prompt + agentConfig | 6 h | AgentConfig update |
| `rag:{sectionId}:{queryHash}` | top-K retrieved chunks | 15 min | knowledge re-ingest |
| `ratelimit:{userId}` | token bucket for chat | 1 min window | — |

- **Progress** uses read-through + write-through: writes upsert the DB then bust
  the key for lazy refill.
- **RAG cache key** = `sha256(sectionId + normalized_query)`; identical questions
  in a section skip the embed + ANN round-trip.
- **Rate limit**: `INCR ratelimit:{userId}` with `EXPIRE 60`; reject over N/min.

## Model selection

- `claude-sonnet-4-6` — default mentor (fast, cheap, strong reasoning).
- `claude-opus-4-8` — deep strategy / critique sections.
- `claude-haiku-4-5` — cheap classification + routing.
- Enable **prompt caching** on the system prompt + retrieved knowledge block to
  cut cost/latency across multi-turn sessions.

## Context-injection payload

The Core API sends this versioned, self-contained payload to the AI layer each
turn (the orchestrator maps it onto the Claude `messages` call):

```json
{
  "schema_version": "1.0",
  "request_id": "req_8f2c...",
  "tenant": { "org_id": "uuid", "plan": "SCALE" },
  "actor": { "user_id": "uuid", "role": "STUDENT", "display_name": "Jordan", "stage": "beginner" },
  "location": {
    "course_id": "uuid", "module_id": "uuid",
    "section_id": "00000000-0000-0000-0000-000000000201",
    "section_title": "Designing Your First Offer", "section_kind": "INTERACTIVE"
  },
  "agent": {
    "persona": "copywriting_mentor", "model": "claude-sonnet-4-6", "temperature": 0.4,
    "allowed_knowledge_tags": ["offers", "copywriting", "growth-operator"]
  },
  "section_content": {
    "objective": "Produce a validated offer with an action-based guarantee.",
    "body_excerpt": "An offer is the transformation sold...",
    "completion_criteria": ["offer_named", "guarantee_defined", "price_set"]
  },
  "progress_signals": {
    "completed_criteria": ["offer_named"], "quiz_scores": [],
    "sections_completed": 4, "last_action_at": "2026-06-11T10:14:00Z"
  },
  "conversation": {
    "history": [
      { "role": "user", "content": "I want to sell a course on email marketing." },
      { "role": "assistant", "content": "Who specifically is it for...?" }
    ],
    "user_message": "It's for freelance designers who want recurring clients."
  },
  "retrieval": { "strategy": "hybrid_rrf_rerank", "top_k": 6 }
}
```

Mapping: `agent.persona` → system prompt; `section_content` + retrieved chunks →
in-context `<knowledge_base>`; `conversation.history` → prior turns;
`progress_signals.completed_criteria` lets the agent push only the *remaining*
criteria; `request_id` threads through traces (Langfuse) back to `section_id`.

## Retrieval quality controls

- Hybrid search: vector ANN + Postgres full-text (`tsvector`) fused via
  reciprocal-rank fusion.
- Voyage `rerank-2` over the top ~20 candidates → keep 6.
- Tag-scoping so a Copywriting section never retrieves Client-Acquisition chunks
  unless relevant.
