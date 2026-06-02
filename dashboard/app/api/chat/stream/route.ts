import { NextRequest } from "next/server";

const PYTHON_BACKEND = process.env.CHAT_BACKEND_URL || "http://localhost:8001";

/**
 * POST /api/chat/stream — SSE endpoint for agent chat.
 *
 * Proxies to the Python backend if available,
 * otherwise returns a helpful fallback message.
 */
export async function POST(req: NextRequest) {
  const body = await req.json();
  const { message, agentId, conversationId } = body;

  // Try to proxy to Python backend
  try {
    const endpoint = agentId
      ? `${PYTHON_BACKEND}/api/v1/chat/direct/stream`
      : `${PYTHON_BACKEND}/api/v1/chat/stream`;

    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        agent_slug: agentId,
        conversation_id: conversationId,
      }),
      signal: AbortSignal.timeout(5000),
    });

    if (res.ok) {
      // Forward the SSE stream
      return new Response(res.body, {
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
        },
      });
    }
  } catch {
    // Backend not available — fall through to mock
  }

  // Fallback: mock agent response for development
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      const agentName = agentId || pickAgent(message);
      const response = generateMockResponse(agentName, message);

      // Simulate typing delay
      for (const chunk of splitChunks(response, 20)) {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ event: "message", content: chunk, agent_id: agentName })}\n\n`)
        );
        await sleep(50);
      }

      // Agent movement event
      controller.enqueue(
        encoder.encode(`data: ${JSON.stringify({ event: "agent-move", agent_id: agentName, room: "War Room" })}\n\n`)
      );

      // Done
      controller.enqueue(
        encoder.encode(`data: ${JSON.stringify({ event: "done" })}\n\n`)
      );
      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}

// ─── Mock helpers (dev mode) ──────────────────────────

function pickAgent(message: string): string {
  const lower = message.toLowerCase();
  if (lower.includes("risk") || lower.includes("stop")) return "risk";
  if (lower.includes("chain") || lower.includes("whale")) return "onchain";
  if (lower.includes("analys") || lower.includes("signal")) return "analyst";
  if (lower.includes("critic") || lower.includes("review")) return "critic";
  if (lower.includes("execut") || lower.includes("trade")) return "engine";
  return "strategist";
}

function generateMockResponse(agentId: string, message: string): string {
  const responses: Record<string, string> = {
    strategist: `🧭 **Strategist Report**\n\nAnalyzing your request: "${message.slice(0, 50)}..."\n\nMarket regime: NEUTRAL\nRecommended action: Hold current positions.\nRisk appetite: 0.6/1.0`,
    analyst: `📊 **Analyst Signal**\n\nBased on EMA/RSI analysis:\n- BTC: Bullish crossover on 4H\n- ETH: RSI at 62, approaching overbought\n- Recommendation: Watch for pullback entries`,
    critic: `🛡️ **Risk Critic Review**\n\nPosition sizing check: ✅ PASS\nMax drawdown: 3.2% (limit: 5%)\nCorrelation risk: LOW\nVerdict: APPROVED with 0.8x size multiplier`,
    onchain: `🔗 **OnChain Signal**\n\n- Exchange outflow: +$12M (bullish)\n- Whale activity: 3 large transfers detected\n- Funding rate: 0.01% (neutral)\n- Composite score: 0.65/1.0`,
    risk: `⚠️ **Risk Manager**\n\nAll circuit breakers: GREEN\nTrailing stop: Active on ETH position\nMax position: 15% of portfolio\nNo emergency actions required.`,
    engine: `⚡ **Execution Engine**\n\nPaper trading mode: ACTIVE\nPending orders: 0\nLast execution: BUY 0.5 ETH @ $3,420\nGas estimate: $0.12 (L2)`,
  };
  return responses[agentId] || `Agent ${agentId} received your message: "${message}"`;
}

function splitChunks(text: string, size: number): string[] {
  const chunks: string[] = [];
  for (let i = 0; i < text.length; i += size) {
    chunks.push(text.slice(i, i + size));
  }
  return chunks;
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}
