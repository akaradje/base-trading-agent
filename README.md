# Base Trading Agent 🤖

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/akaradje/base-trading-agent?style=social)](https://github.com/akaradje/base-trading-agent/stargazers)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/akaradje/base-trading-agent)](https://github.com/akaradje/base-trading-agent/commits)
[![GitHub Issues](https://img.shields.io/github/issues/akaradje/base-trading-agent)](https://github.com/akaradje/base-trading-agent/issues)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](deploy/Dockerfile)
[![Supabase](https://img.shields.io/badge/Supabase-Realtime-3FCF8E?logo=supabase&logoColor=white)](https://supabase.com/)
[![Base Blockchain](https://img.shields.io/badge/Base-L2-0052FF?logo=ethereum&logoColor=white)](https://base.org/)

A **multi-agent** cryptocurrency trading bot for the **Base blockchain** (Coinbase L2). Runs **24/7** with a Planner–Analyst–Critic–Executor pipeline. Starts in **paper trading** mode (simulated, no real money) and can be switched to live trading later.

> ⚠️ **Disclaimer:** This is educational/experimental software, not financial advice. Crypto is highly volatile. Always start with paper trading and never invest more than you can afford to lose.

---

## Multi-Agent Architecture

```
Prices (CoinGecko) ─► Indicators (EMA/RSI)
                         │
   ┌─────────────────────┴───────────────────────────────┐
   │ 0. RiskManager (deterministic): kill switch,         │
   │    stop-loss / take-profit  ── always enforced ──┐   │
   │ 1. 🧭 Strategist (Planner)  regime/risk appetite    │
   │ 2. 📊 Analyst  conviction + action (price action)   │
   │ 3. 🛡️ RiskCritic (Critic)  approve/veto/shrink      │
   │ 4. ⚙️ Executor  place orders (paper / Base)          │
   └──────────────────────────────────────────────────────┘
```

Hard risk rules (stop-loss, take-profit, position caps, kill switch) are enforced by **deterministic code** — LLMs can only filter out or reduce trade size, never bypass these rules.

### Models (via OpenRouter — cost-optimized selection)

| Agent | Model | Price /1M (in/out) |
|---|---|---|
| 🧭 Strategist | `qwen/qwen3.7-max` | ~$0.25 / $0.38 |
| 📊 Analyst | `qwen/qwen3-coder-flash` | $0.07 / $0.26 |
| 🛡️ RiskCritic | `xiaomi/mimo-v2.5-pro` | reasoning model |

Change models in `config.yaml` → `agents:` (see all slugs at https://openrouter.ai/models)

---

## Installation

```bash
pip install -r requirements.txt

# (Optional) Add LLM key — bot runs with deterministic strategy without it
copy .env.example .env        # Windows
# Edit .env and add OPENROUTER_API_KEY
```

Set env var (PowerShell):
```powershell
$env:OPENROUTER_API_KEY = "sk-or-..."
```

---

## Usage

```bash
python run.py backtest --days 90   # Backtest base strategy with historical data
python run.py run                  # Start 24/7 paper trading bot (Ctrl+C to stop)
python run.py status               # View latest portfolio status
```

Portfolio state is saved to `state/portfolio.json` (resumes after restart).

---

## Configuration (`config.yaml`)

- `mode`: `paper` (simulated) | `live` (blocked — requires Base MCP connection)
- `poll_interval_sec`: price check interval (default 60s)
- `symbols`: coins to trade (use **CoinGecko coin id**)
- `strategy`: EMA/RSI parameters
- `risk`: stop-loss, take-profit, position caps, max-drawdown, fees
- `agents`: enable/disable + select model for each agent

---

## Going Live on Base (Future)

Currently `LiveExecutor` is blocked to prevent accidental real-money trades. To enable:

1. Install Base MCP: `claude mcp add --transport http base-mcp https://mcp.base.org`
2. Edit `basebot/executor.py` → `LiveExecutor.buy/sell` to call swaps via Base MCP
   (ETH/USDC ↔ token) — every write action includes an **approve link in Base Account** before confirmation
3. Set `mode: live` in `config.yaml`

---

## Project Structure

```
run.py                  CLI (run / backtest / status)
config.yaml             All configuration
basebot/
  config.py             Load config
  data.py               CoinGecko price fetcher
  indicators.py         EMA / RSI / crossover
  portfolio.py          Simulated portfolio + persistence
  risk.py               Deterministic risk rules
  executor.py           Paper / Live executor
  llm.py                OpenRouter client (OpenAI-compatible)
  orchestrator.py       Agent coordination (Planner→Analyst→Critic→Executor)
  engine.py             24/7 trading loop
  backtest.py           Historical backtesting
  agents/               strategist, analyst, risk_critic
```

---

## License

[MIT](LICENSE)
