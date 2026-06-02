# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent cryptocurrency trading bot for **Base blockchain** tokens (Coinbase L2). Currently in **paper trading** mode. Uses LLMs via OpenRouter for decision-making with a deterministic EMA/RSI fallback when no API key is set. Comments and README are in **Thai**.

## Commands

```bash
pip install -r requirements.txt       # Install dependencies (requests, PyYAML, openai)
python run.py run                     # Start 24/7 paper trading bot (Ctrl+C to stop)
python run.py backtest --days 90      # Backtest deterministic strategy (no LLM)
python run.py status                  # Show portfolio state
python run.py health                  # Check bot health (heartbeat)
python run.py --config path/to.yaml run  # Custom config
python -m compileall -q basebot run.py   # Syntax check (no test suite exists)
```

Set `OPENROUTER_API_KEY` in `.env` (see `.env.example`) for LLM-powered agents. Without it, the bot runs in deterministic-only mode.

Optional env vars for on-chain signals and alerting:
- `GLASSNODE_API_KEY` — exchange flow signal (Glassnode)
- `BASESCAN_API_KEY` — whale tracking on Base (Basescan)
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` — Telegram alerts

## Architecture

The pipeline is a multi-agent loop with deterministic safety rails that **always override** LLM output:

```
CoinGecko prices → EMA/RSI/ATR/Bollinger indicators
       │
  0. RiskManager (deterministic): stop-loss, take-profit, trailing stop, tiered circuit breakers
  0.5. Connectivity Kill Switch: data stale > 3 cycles → sell everything
  1. Strategist (LLM): market regime (risk_on/neutral/risk_off), allowed symbols
  1.5. OnChain Agent (deterministic): exchange flow, funding rate, whale signals → composite score
  1.6. Liquidation Cascade (deterministic): OI drop + price move → mean-reversion signal (1.5x boost)
  2. Analyst (LLM): action + conviction (assesses momentum from price action)
  3. RiskCritic (LLM): approve/veto/shrink position size (called before chain conviction)
  4. Confidence-Weighted Consensus: appetite × analyst_conv × onchain_conv × critic_size × cascade_boost
  5. Executor: paper trade or on-chain swap (LiveExecutor uses GasOracle for L1/L2 fee breakdown)
  6. Alerts: Telegram notifications for kill switches, emergencies, daily P&L
  7. Training Collector: logs decisions + outcomes for LoRA fine-tuning
```

**Key invariant:** `risk.py` enforces stop-loss, take-profit, max position size, trailing stops, and tiered circuit breakers in code. LLM agents can only *reduce* trade activity, never increase it beyond these limits.

## Source Layout

| File | Role |
|---|---|
| `run.py` | CLI entry point (argparse: `run`, `backtest`, `status`, `health`) |
| `config.yaml` | All configuration — mode, symbols, strategy params, risk params, agent models, onchain, alerts |
| `basebot/config.py` | Loads `config.yaml` into `Config` dataclass |
| `basebot/data.py` | CoinGecko API client with retry/backoff, OHLC endpoint |
| `basebot/indicators.py` | Pure-Python EMA, RSI (Wilder), ATR, Bollinger Bands, crossover detection |
| `basebot/portfolio.py` | Simulated portfolio with JSON persistence to `state/portfolio.json` (atomic save) |
| `basebot/risk.py` | Deterministic risk rules — trailing stops, tiered circuit breakers, ATR-weighted sizing |
| `basebot/executor.py` | `PaperExecutor` + `LiveExecutor` + `GasOracle` + `Multicall3Client` (batch reads) |
| `basebot/llm.py` | OpenRouter client (OpenAI SDK). Forces JSON output. Graceful None on failure |
| `basebot/orchestrator.py` | Full pipeline: risk exits → kill switch → strategist → onchain → liquidation → analyst → critic → consensus → executor |
| `basebot/engine.py` | 24/7 loop: warmup → poll/orchestrate/save + connectivity kill switch + heartbeat healthcheck |
| `basebot/backtest.py` | Historical replay, deterministic strategy only |
| `basebot/alerts.py` | Telegram notifications for kill switches, emergencies, daily P&L |
| `basebot/liquidation.py` | Liquidation cascade detection (OI tracking, mean-reversion signals) |
| `basebot/agents/` | `strategist.py`, `analyst.py`, `risk_critic.py`, `onchain.py` |
| `basebot/training/` | LoRA fine-tuning: `collector.py`, `dataset.py`, `train.py`, `inference.py` |

## LLM Configuration

Agents use OpenRouter with cost-optimized models configured in `config.yaml`:
- **Strategist:** `qwen/qwen3.7-max`
- **Analyst:** `qwen/qwen3-coder-flash`
- **RiskCritic:** `xiaomi/mimo-v2.5-pro`

All agents force structured JSON output via `response_format=json_object` and schema in system prompts. The `_extract_json` helper in `llm.py` handles markdown code fences.

## Dashboard

Real-time monitoring dashboard built with **Next.js 15 + Phaser 3 + Supabase + ECharts**.

```bash
cd dashboard && npm install   # Install dependencies
npm run dev                   # Start dev server (localhost:3000)
npm run build                 # Production build
```

**Architecture:**
- **Phaser 3 canvas** renders a pixel-art isometric office with animated agent sprites
- **React overlay** provides chat, analytics, and UI panels on top of the canvas
- **EventBus** singleton bridges Phaser ↔ React for all interactions
- **Supabase Realtime** subscribes to agent_states, portfolio, trades tables
- **SSE Chat** streams agent responses via `/api/chat/stream` (proxies to `basebot.chat_server`)

**Key files:**
| File | Role |
|---|---|
| `dashboard/phaser/` | Phaser 3 scenes (Boot, Preload, Office) |
| `dashboard/lib/EventBus.ts` | Phaser ↔ React event bridge |
| `dashboard/components/chat/` | Chat UI (ChatBox, ContactList, Message, Input) |
| `dashboard/components/analytics/` | ECharts dashboards (tokens, P&L, activity, cost) |
| `dashboard/components/office/` | AgentStatusBar, PhaserGame wrapper |
| `dashboard/app/api/chat/stream/` | Next.js API route → Python chat server proxy |
| `basebot/chat_server.py` | FastAPI SSE server wrapping agent pipeline |

**Run chat backend:**
```bash
pip install fastapi uvicorn
python -m basebot.chat_server  # Starts on port 8001
```

## Development Notes

- **No test suite, linter, formatter, or CI/CD exists.** Use `python -m compileall -q basebot run.py` to catch syntax errors.
- Portfolio state persists to `basebot/state/portfolio.json` (gitignored).
- `LiveExecutor` is intentionally unimplemented — intended for Base MCP on-chain swaps.
- The Strategist agent result is cached and refreshes every ~30 min.
- `.env` and `state/` are gitignored — never commit API keys or portfolio state.
- **Deployment:** `deploy/` contains systemd service, Dockerfile, and docker-compose.yml. Use `python run.py health` for healthcheck (exit 0=healthy, 1=unhealthy).
