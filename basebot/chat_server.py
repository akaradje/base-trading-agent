"""
Chat SSE server — exposes the agent pipeline via Server-Sent Events.

Endpoints:
  POST /api/v1/chat/stream         — group chat (dispatcher routes to agent)
  POST /api/v1/chat/direct/stream  — DM to a specific agent

Run with:
  python -m basebot.chat_server
"""

import asyncio
import json
import time
import uuid
from typing import AsyncGenerator

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    raise ImportError("pip install fastapi uvicorn — required for chat server")

from basebot.config import load_config
from basebot.llm import chat_completion

app = FastAPI(title="Base Trading Agent Chat Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Agent definitions ─────────────────────────────────

AGENTS = {
    "strategist": {
        "name": "Jing",
        "role": "Strategist",
        "system_prompt": (
            "You are Jing, the Strategist agent in a crypto trading team on Base blockchain. "
            "You analyze market regimes (risk_on/neutral/risk_off) and recommend which symbols to trade. "
            "Respond in Thai or English. Be concise. Format with markdown."
        ),
    },
    "analyst": {
        "name": "Joe",
        "role": "Analyst",
        "system_prompt": (
            "You are Joe, the Analyst agent. You assess momentum from EMA/RSI/ATR/Bollinger indicators "
            "and generate trading signals with conviction scores (0-1). Respond concisely with markdown."
        ),
    },
    "critic": {
        "name": "James",
        "role": "RiskCritic",
        "system_prompt": (
            "You are James, the RiskCritic agent. You review proposed trades and decide to APPROVE, VETO, "
            "or SHRINK position size. You look for correlated risk, oversized positions, and bad timing. "
            "Be brief and decisive."
        ),
    },
    "onchain": {
        "name": "Jade",
        "role": "OnChain",
        "system_prompt": (
            "You are Jade, the OnChain agent. You monitor exchange flows, whale activity, and funding rates "
            "on Base blockchain. You produce composite scores from on-chain data. Respond with data points."
        ),
    },
    "risk": {
        "name": "Jeed",
        "role": "RiskMgr",
        "system_prompt": (
            "You are Jeed, the Risk Manager. You enforce stop-loss, take-profit, trailing stops, "
            "and circuit breakers. You are deterministic and never compromise on risk limits. "
            "Report current risk status concisely."
        ),
    },
    "engine": {
        "name": "Jai",
        "role": "Engine",
        "system_prompt": (
            "You are Jai, the Execution Engine. You handle paper trades and on-chain swaps. "
            "Report execution status, gas estimates, and trade confirmations. Be brief."
        ),
    },
}

DISPATCHER_PROMPT = (
    "You are the dispatcher for a crypto trading team. Based on the user's message, "
    "decide which agent should respond. Available agents:\n"
    + "\n".join(f"- {k}: {v['role']} — {v['name']}" for k, v in AGENTS.items())
    + "\n\nRespond with ONLY the agent slug (e.g. 'strategist') on the first line, "
    "then the user's question on the second line. If the question is general, use 'strategist'."
)


# ─── SSE helpers ────────────────────────────────────────

def sse_event(event: str, data: dict) -> str:
    return f"data: {json.dumps({'event': event, **data})}\n\n"


# ─── Endpoints ──────────────────────────────────────────

@app.post("/api/v1/chat/stream")
async def chat_stream(request: Request):
    body = await request.json()
    message = body.get("message", "")
    conversation_id = body.get("conversation_id", str(uuid.uuid4()))

    async def generate() -> AsyncGenerator[str, None]:
        # Step 1: Dispatch to the right agent
        yield sse_event("dispatcher", {"content": "Routing to agent..."})

        try:
            dispatch_response = await asyncio.to_thread(
                chat_completion,
                [
                    {"role": "system", "content": DISPATCHER_PROMPT},
                    {"role": "user", "content": message},
                ],
                temperature=0.1,
                max_tokens=50,
            )
            agent_id = dispatch_response.strip().split("\n")[0].strip().lower()
            if agent_id not in AGENTS:
                agent_id = "strategist"
        except Exception:
            agent_id = "strategist"

        agent = AGENTS[agent_id]
        yield sse_event("dispatcher", {"content": f"→ {agent['name']} ({agent['role']})", "agent_id": agent_id})

        # Step 2: Stream the agent's response
        try:
            response = await asyncio.to_thread(
                chat_completion,
                [
                    {"role": "system", "content": agent["system_prompt"]},
                    {"role": "user", "content": message},
                ],
                temperature=0.7,
                max_tokens=500,
            )

            # Stream in chunks for typing effect
            chunk_size = 30
            for i in range(0, len(response), chunk_size):
                chunk = response[i : i + chunk_size]
                yield sse_event("message", {"content": chunk, "agent_id": agent_id})
                await asyncio.sleep(0.05)

        except Exception as e:
            yield sse_event("error", {"message": str(e)})

        # Step 3: Agent movement event
        yield sse_event("agent-move", {"agent_id": agent_id, "room": "War Room"})
        yield sse_event("done", {})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/api/v1/chat/direct/stream")
async def direct_chat_stream(request: Request):
    body = await request.json()
    message = body.get("message", "")
    agent_id = body.get("agent_slug", "strategist")

    if agent_id not in AGENTS:
        agent_id = "strategist"

    agent = AGENTS[agent_id]

    async def generate() -> AsyncGenerator[str, None]:
        try:
            response = await asyncio.to_thread(
                chat_completion,
                [
                    {"role": "system", "content": agent["system_prompt"]},
                    {"role": "user", "content": message},
                ],
                temperature=0.7,
                max_tokens=500,
            )

            chunk_size = 30
            for i in range(0, len(response), chunk_size):
                chunk = response[i : i + chunk_size]
                yield sse_event("message", {"content": chunk, "agent_id": agent_id})
                await asyncio.sleep(0.05)

        except Exception as e:
            yield sse_event("error", {"message": str(e)})

        yield sse_event("agent-move", {"agent_id": agent_id, "room": "War Room"})
        yield sse_event("done", {})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "agents": list(AGENTS.keys())}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
