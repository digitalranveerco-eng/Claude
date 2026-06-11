"""FastAPI AI orchestration layer.

Pipeline per turn: resolve agent config -> RAG retrieve -> assemble messages ->
stream completion from Claude -> persist the turn with token usage + context tags.
"""

import json
import os

from anthropic import Anthropic
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from db import init_pool, close_pool, tenant_conn
from prompts import ATLAS_SYSTEM_PROMPT, build_knowledge_block
from retrieval import retrieve

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
app = FastAPI(title="Growth Operator AI Orchestration")

DEFAULT_MODEL = "claude-sonnet-4-6"  # escalate to claude-opus-4-8 for deep strategy


@app.on_event("startup")
async def _startup() -> None:
    await init_pool()


@app.on_event("shutdown")
async def _shutdown() -> None:
    await close_pool()


class Turn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    org_id: str
    user_id: str
    session_id: str
    section_id: str
    user_message: str
    history: list[Turn] = []


async def load_agent_config(org_id: str, section_id: str) -> dict:
    """Fetch persona/prompt/model/tags for the section, with sensible defaults."""
    async with tenant_conn(org_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT persona, "systemPrompt", model, temperature, "knowledgeTags"
            FROM "AgentConfig" WHERE "sectionId" = $1
            """,
            section_id,
        )
    if row is None:
        return {
            "persona": "copywriting_mentor",
            "system_prompt": ATLAS_SYSTEM_PROMPT,
            "model": DEFAULT_MODEL,
            "temperature": 0.4,
            "tags": ["growth-operator", "copywriting", "offers"],
        }
    return {
        "persona": row["persona"],
        "system_prompt": row["systemPrompt"] or ATLAS_SYSTEM_PROMPT,
        "model": row["model"] or DEFAULT_MODEL,
        "temperature": row["temperature"],
        "tags": list(row["knowledgeTags"]),
    }


async def persist_turn(req: ChatRequest, answer: str, usage, model: str, tags: list[str]) -> None:
    async with tenant_conn(req.org_id) as conn:
        await conn.execute(
            """
            INSERT INTO "ChatMessage"
              (id,"sessionId",role,content,"inputTokens","outputTokens",model,"contextTags","sectionId","createdAt")
            VALUES
              (gen_random_uuid(),$1,'USER',$2,0,0,NULL,$5,$6,now()),
              (gen_random_uuid(),$1,'ASSISTANT',$3,$4,$7,$8,$5,$6,now())
            """,
            req.session_id, req.user_message, answer,
            usage.input_tokens, tags, req.section_id, usage.output_tokens, model,
        )


@app.post("/v1/chat/stream")
async def chat_stream(req: ChatRequest):
    cfg = await load_agent_config(req.org_id, req.section_id)
    chunks = await retrieve(req.org_id, req.user_message, cfg["tags"])
    knowledge = build_knowledge_block(chunks)

    messages = [{"role": t.role, "content": t.content} for t in req.history]
    messages.append(
        {"role": "user", "content": f"{knowledge}\n\nUser: {req.user_message}"}
    )

    async def gen():
        collected = []
        with client.messages.stream(
            model=cfg["model"],
            max_tokens=1500,
            temperature=cfg["temperature"],
            system=cfg["system_prompt"],
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                collected.append(text)
                yield f"data: {json.dumps({'delta': text})}\n\n"
            final = stream.get_final_message()
        answer = "".join(collected)
        await persist_turn(req, answer, final.usage, cfg["model"], cfg["tags"])
        yield f"data: {json.dumps({'done': True, 'tags': cfg['tags']})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
