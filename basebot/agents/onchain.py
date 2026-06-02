"""OnChain Agent — รวบรวมสัญญาณ on-chain 3 ชนิด: exchange flow, funding rate, whale accumulation.

สัญญาณเหล่านี้ไม่ต้องใช้ LLM — ดึงข้อมูลจาก API แล้วคำนวณ deterministic
ผลลัพธ์เป็น composite score [-1, 1] ที่ orchestrator ใช้ชั่งน้ำหนักในการตัดสินใจเทรด

สัญญาณ:
  1. Exchange Flow (Glassnode): net outflow = bullish, net inflow = bearish
  2. Funding Rate (Binance Futures): crowded longs = bearish, crowded shorts = bullish
  3. Whale Accumulation (Basescan): 3+ wallets สะสมเหรียญเดียวกัน = bullish
"""
from __future__ import annotations

import os
import time

import requests

_session = requests.Session()
_session.headers.update({"User-Agent": "base-trading-agent/0.1"})


def _get_json(url: str, params: dict | None = None, headers: dict | None = None,
              timeout: int = 15) -> dict | list | None:
    """GET JSON with basic error handling. Returns None on failure."""
    try:
        r = _session.get(url, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ──────────────────────────────────────────────
# Signal 1: Exchange Flow (Binance trades — proxy, ไม่ต้องมี API key)
# ──────────────────────────────────────────────

def _exchange_flow_signal(api_key: str = "", asset: str = "ETH") -> float | None:
    """Net exchange flow จาก Binance trades — normalize เป็น [-1, 1].

    ใช้ buy vs sell volume จาก Binance trades เป็น proxy สำหรับ exchange flow:
    - Net buy volume > sell volume = bullish (+1)
    - Net sell volume > buy volume = bearish (-1)

    ไม่ต้องมี API key — ใช้ Binance public API
    """
    symbol = f"{asset}USDT"
    data = _get_json(
        "https://api.binance.com/api/v3/trades",
        {"symbol": symbol, "limit": 1000},
    )

    if not data or not isinstance(data, list) or len(data) < 100:
        return None

    # คำนวณ buy vs sell volume
    buy_vol = 0.0
    sell_vol = 0.0
    for trade in data:
        qty = float(trade.get("qty", 0))
        if trade.get("isBuyerMaker"):
            sell_vol += qty  # seller is maker = sell pressure
        else:
            buy_vol += qty   # buyer is maker = buy pressure

    total = buy_vol + sell_vol
    if total <= 0:
        return None

    # Net flow ratio: +1 = all buy, -1 = all sell
    net_ratio = (buy_vol - sell_vol) / total

    # Clamp to [-1, 1]
    return max(-1.0, min(1.0, net_ratio))


# ──────────────────────────────────────────────
# Signal 2: Funding Rate (Binance Futures)
# ──────────────────────────────────────────────

def _funding_rate_signal(symbol: str = "ETHUSDT") -> float | None:
    """Funding rate จาก Binance Futures — normalize เป็น [-1, 1].

    Funding > 0.1%/8h = bearish (-1) — crowded longs
    Funding < -0.05%/8h = bullish (+1) — crowded shorts
    ระหว่างนั้น interpolate linearly
    """
    # Binance public API — ไม่ต้องมี key
    data = _get_json(
        "https://fapi.binance.com/fapi/v1/fundingRate",
        {"symbol": symbol, "limit": 3},
    )
    if not data or not isinstance(data, list) or len(data) < 1:
        return None

    # ใช้ค่าล่าสุด
    rate = float(data[-1].get("fundingRate", 0))
    # rate เป็น decimal (0.0001 = 0.01%)
    rate_pct = rate * 100  # เปลี่ยนเป็น %

    # Normalize: -0.05% → +1 (bullish), +0.1% → -1 (bearish)
    if rate_pct >= 0:
        # bearish zone: 0% ถึง 0.1%+ → 0 ถึง -1
        signal = max(-1.0, -rate_pct / 0.1)
    else:
        # bullish zone: 0% ถึง -0.05% → 0 ถึง +1
        signal = min(1.0, rate_pct / 0.05)

    return signal


# ──────────────────────────────────────────────
# Signal 3: Whale Accumulation (Basescan)
# ──────────────────────────────────────────────

def _whale_signal(api_key: str, watchlist: list[str], token_address: str | None = None) -> float | None:
    """ติดตาม whale wallets บน Base ผ่าน Basescan API.

    ถ้า 3+ wallets สะสม token เดียวกันภายใน 48 ชม. → signal = +1
    ถ้า 2 wallets → +0.5
    ถ้า 1 wallet → +0.25
    ถ้า 0 → 0
    """
    if not api_key or not watchlist:
        return None

    accumulating = 0
    for wallet in watchlist[:20]:  # จำกัดไม่เกิน 20 wallets
        params = {
            "module": "account",
            "action": "tokentx",
            "address": wallet,
            "page": 1,
            "offset": 10,
            "sort": "desc",
            "apikey": api_key,
        }
        if token_address:
            params["contractaddress"] = token_address

        data = _get_json("https://api.basescan.org/api", params)
        if not data or data.get("status") != "1":
            continue

        txs = data.get("result", [])
        # ตรว 48 ชม. — นับ transfer ที่เข้า wallet (to == wallet)
        now = time.time()
        recent_inflows = 0
        for tx in txs:
            ts = int(tx.get("timeStamp", 0))
            if now - ts > 86400 * 2:  # 48 ชม.
                break
            if tx.get("to", "").lower() == wallet.lower():
                recent_inflows += 1

        if recent_inflows >= 1:
            accumulating += 1

    if accumulating >= 3:
        return 1.0
    if accumulating == 2:
        return 0.5
    if accumulating == 1:
        return 0.25
    return 0.0


# ──────────────────────────────────────────────
# OnChain Agent — รวมทุกสัญญาณ
# ──────────────────────────────────────────────

# Config weights (default)
_DEFAULT_WEIGHTS = {
    "exchange_flow": 0.35,
    "funding_rate": 0.35,
    "whale": 0.30,
}


class OnChainAgent:
    """Agent ดึงสัญญาณ on-chain — ไม่ใช้ LLM, ทำงาน deterministic ทั้งหมด."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.cryptoquant_key = cfg.get("cryptoquant_api_key") or os.environ.get("CRYPTOQUANT_API_KEY", "")
        self.basescan_key = cfg.get("basescan_api_key") or os.environ.get("BASESCAN_API_KEY", "")
        self.whale_watchlist = cfg.get("whale_watchlist", [])
        self.weights = cfg.get("weights", _DEFAULT_WEIGHTS)
        self._cache: dict = {}
        self._cache_ts: float = 0
        self._cache_ttl = int(cfg.get("poll_interval_min", 15)) * 60

    def signals(self) -> dict:
        """ดึงสัญญาณ on-chain ทั้งหมด — ใช้ cache ตาม poll_interval.

        คืน dict:
        {
            "exchange_flow": float | None,
            "funding_rate": float | None,
            "whale": float | None,
            "composite_score": float,     # weighted average (ข้าม None)
            "conviction": float,          # 0-1, ยิ่งสัญญาณเห็นตรงกันยิ่งสูง
            "summary": str,
        }
        """
        now = time.time()
        if now - self._cache_ts < self._cache_ttl and self._cache:
            return self._cache

        ef = _exchange_flow_signal(self.cryptoquant_key)
        fr = _funding_rate_signal()
        wh = _whale_signal(self.basescan_key, self.whale_watchlist)

        # Composite score — weighted average ข้าม None
        scores = {}
        weights = {}
        for key, val in [("exchange_flow", ef), ("funding_rate", fr), ("whale", wh)]:
            if val is not None:
                scores[key] = val
                weights[key] = self.weights.get(key, 0.33)

        if weights:
            total_w = sum(weights.values())
            composite = sum(scores[k] * weights[k] for k in scores) / total_w
        else:
            composite = 0.0

        # Conviction — ยิ่งสัญญาณเห็นตรงกัน ยิ่งสูง
        vals = list(scores.values())
        if len(vals) >= 2:
            # ถ้าทุกสัญญาณชี้ทางเดียวกัน → conviction สูง
            signs = [1 if v > 0.1 else (-1 if v < -0.1 else 0) for v in vals]
            agreement = abs(sum(signs)) / len(signs)
            magnitude = sum(abs(v) for v in vals) / len(vals)
            conviction = min(1.0, agreement * 0.6 + magnitude * 0.4)
        elif len(vals) == 1:
            conviction = abs(vals[0]) * 0.5
        else:
            conviction = 0.0

        # Summary
        parts = []
        if ef is not None:
            parts.append(f"exchange_flow={ef:+.2f}")
        if fr is not None:
            parts.append(f"funding={fr:+.2f}")
        if wh is not None:
            parts.append(f"whale={wh:+.2f}")
        summary = ", ".join(parts) if parts else "no on-chain data"

        result = {
            "exchange_flow": ef,
            "funding_rate": fr,
            "whale": wh,
            "composite_score": round(composite, 4),
            "conviction": round(conviction, 4),
            "summary": summary,
        }

        self._cache = result
        self._cache_ts = now
        return result
