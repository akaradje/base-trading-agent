"""ดึงราคาเหรียญจากหลายแหล่ง — Binance (หลัก) + DeFiLlama (fallback) + CoinGecko (last resort).

Binance: 1,200 req/min, ไม่ต้องมี API key, OHLC klines ทุก timeframe
DeFiLlama: ไม่จำกัด rate, ไม่ต้องมี API key, historical prices
CoinGecko: 10-50 req/min (free tier) — ใช้เฉพาะเหรียญที่ไม่มีใน Binance/DeFiLlama

ลำดับการดึง:
  1. Binance (เร็วสุด, rate limit สูงสุด)
  2. DeFiLlama (ไม่จำกัด rate, แต่ไม่มี OHLC ทุก timeframe)
  3. CoinGecko (last resort, rate limit ต่ำ)
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import requests

# ──────────────────────────────────────────────
# Shared
# ──────────────────────────────────────────────

_session = requests.Session()
_session.headers.update({"User-Agent": "base-trading-agent/0.1"})


class DataError(RuntimeError):
    pass


def _safe_get(url: str, params: dict | None = None, timeout: int = 15,
              retries: int = 2) -> dict | list | None:
    """GET JSON with retry. คืน None ถ้า fail (ไม่ raise)."""
    for attempt in range(retries):
        try:
            r = _session.get(url, params=params, timeout=timeout)
            if r.status_code == 429:
                wait = int(r.headers.get("retry-after", 10))
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt < retries - 1:
                time.sleep(1 + attempt)
    return None


# ──────────────────────────────────────────────
# CoinGecko ID → Binance Symbol Mapping
# ──────────────────────────────────────────────

_COINGECKO_TO_BINANCE: dict[str, str] = {
    "ethereum": "ETHUSDT",
    "aerodrome-finance": "AEROUSDT",
    "degen-base": "DEGENUSDT",
}

# Reverse mapping สำหรับ lookup
_BINANCE_TO_COINGECKO: dict[str, str] = {v: k for k, v in _COINGECKO_TO_BINANCE.items()}


# ──────────────────────────────────────────────
# Binance API (Primary — 1,200 req/min)
# ──────────────────────────────────────────────

_BINANCE_BASE = "https://api.binance.com/api/v3"


def _binance_current_prices(ids: list[str], vs: str = "usd") -> dict[str, float]:
    """ราคาปัจจุบันจาก Binance — ดึงทีเดียวหลายเหรียญ (1 request)."""
    vs_upper = vs.upper()
    symbols = []
    id_to_symbol = {}
    for cid in ids:
        sym = _COINGECKO_TO_BINANCE.get(cid)
        if sym:
            symbols.append(sym)
            id_to_symbol[cid] = sym

    if not symbols:
        return {}

    data = _safe_get(f"{_BINANCE_BASE}/ticker/price", {"symbols": str(symbols)})
    if not data or not isinstance(data, list):
        return {}

    out: dict[str, float] = {}
    for item in data:
        sym = item.get("symbol", "")
        price = float(item.get("price", 0))
        # แปลงกลับเป็น coin_id
        for cid, mapped_sym in id_to_symbol.items():
            if mapped_sym == sym and price > 0:
                out[cid] = price
    return out


def _binance_klines(symbol: str, interval: str = "1d",
                    limit: int = 30) -> list[dict]:
    """OHLC klines จาก Binance.

    interval: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
    """
    data = _safe_get(f"{_BINANCE_BASE}/klines", {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    })
    if not data or not isinstance(data, list):
        return []

    result = []
    for k in data:
        # [open_time, open, high, low, close, volume, close_time, ...]
        result.append({
            "ts": int(k[0]),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        })
    return result


def _binance_history(coin_id: str, days: int = 30, vs: str = "usd") -> list[float]:
    """ราคาย้อนหลังจาก Binance klines (close prices)."""
    sym = _COINGECKO_TO_BINANCE.get(coin_id)
    if not sym:
        return []

    # เลือก interval ตามจำนวนวัน
    if days <= 1:
        interval, limit = "1h", 24
    elif days <= 7:
        interval, limit = "4h", min(days * 6, 200)
    elif days <= 30:
        interval, limit = "1d", days
    else:
        interval, limit = "1d", min(days, 1000)

    klines = _binance_klines(sym, interval, limit)
    return [k["close"] for k in klines]


def _binance_ohlc(coin_id: str, days: int = 30, vs: str = "usd") -> list[dict]:
    """OHLC จาก Binance klines."""
    sym = _COINGECKO_TO_BINANCE.get(coin_id)
    if not sym:
        return []

    # เลือก interval ตามจำนวนวัน
    if days <= 1:
        interval, limit = "1h", 24
    elif days <= 7:
        interval, limit = "4h", min(days * 6, 200)
    elif days <= 30:
        interval, limit = "1d", days
    else:
        interval, limit = "1d", min(days, 1000)

    return _binance_klines(sym, interval, limit)


# ──────────────────────────────────────────────
# DeFiLlama API (Fallback — ไม่จำกัด rate)
# ──────────────────────────────────────────────

_LLAMA_BASE = "https://coins.llama.fi"


def _llama_current_prices(ids: list[str], vs: str = "usd") -> dict[str, float]:
    """ราคาปัจจุบันจาก DeFiLlama — ดึงทีเดียวหลายเหรียญ (1 request)."""
    coins = ",".join(f"coingecko:{cid}" for cid in ids)
    data = _safe_get(f"{_LLAMA_BASE}/prices/current/{coins}")
    if not data or not isinstance(data, dict):
        return {}

    out: dict[str, float] = {}
    coins_data = data.get("coins", {})
    for cid in ids:
        key = f"coingecko:{cid}"
        coin = coins_data.get(key)
        if coin and "price" in coin:
            out[cid] = float(coin["price"])
    return out


def _llama_history(coin_id: str, days: int = 30, vs: str = "usd") -> list[float]:
    """ราคาย้อนหลังจาก DeFiLlama."""
    now = int(time.time())
    start = now - days * 86400
    data = _safe_get(f"{_LLAMA_BASE}/chart/coingecko:{coin_id}", {
        "start": start,
        "span": days * 86400,
        "period": "1d" if days > 1 else "1h",
    })
    if not data or not isinstance(data, dict):
        return []

    coins = data.get("coins", {})
    coin_data = coins.get(f"coingecko:{coin_id}", {})
    prices = coin_data.get("prices", [])
    return [float(p.get("price", 0)) for p in prices if "price" in p]


# ──────────────────────────────────────────────
# CoinGecko API (Last Resort — rate limited)
# ──────────────────────────────────────────────

_CG_BASE = "https://api.coingecko.com/api/v3"
_last_cg_ts: float = 0
_CG_INTERVAL = 6.0  # 6 วินาทีระหว่าง requests


def _cg_get(path: str, params: dict, retries: int = 2) -> dict | list | None:
    """CoinGecko GET with rate limiting."""
    global _last_cg_ts
    url = f"{_CG_BASE}{path}"
    for attempt in range(retries):
        elapsed = time.time() - _last_cg_ts
        if elapsed < _CG_INTERVAL:
            time.sleep(_CG_INTERVAL - elapsed)
        _last_cg_ts = time.time()

        try:
            r = _session.get(url, params=params, timeout=20)
            if r.status_code == 429:
                wait = int(r.headers.get("retry-after", 15))
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return None


def _cg_current_prices(ids: list[str], vs: str = "usd") -> dict[str, float]:
    """ราคาปัจจุบันจาก CoinGecko."""
    data = _cg_get("/simple/price", {"ids": ",".join(ids), "vs_currencies": vs})
    if not data or not isinstance(data, dict):
        return {}
    out: dict[str, float] = {}
    for cid in ids:
        node = data.get(cid)
        if node and vs in node:
            out[cid] = float(node[vs])
    return out


def _cg_history(coin_id: str, days: int = 30, vs: str = "usd") -> list[float]:
    """ราคาย้อนหลังจาก CoinGecko."""
    data = _cg_get(f"/coins/{coin_id}/market_chart", {"vs_currency": vs, "days": days})
    if not data or not isinstance(data, dict):
        return []
    prices = data.get("prices", [])
    return [float(p[1]) for p in prices]


def _cg_ohlc(coin_id: str, days: int = 30, vs: str = "usd") -> list[dict]:
    """OHLC จาก CoinGecko."""
    raw = _cg_get(f"/coins/{coin_id}/ohlc", {"vs_currency": vs, "days": days})
    if not raw or not isinstance(raw, list):
        return []
    return [
        {"ts": p[0], "open": p[1], "high": p[2], "low": p[3], "close": p[4]}
        for p in raw
    ]


# ──────────────────────────────────────────────
# Multi-Source Public API (ใช้ตัวนี้เท่านั้น)
# ──────────────────────────────────────────────

def current_prices(ids: list[str], vs: str = "usd") -> dict[str, float]:
    """ราคาปัจจุบันของหลายเหรียญ -> {coin_id: price}.

    ลำดับ: Binance → DeFiLlama → CoinGecko
    """
    # 1) Binance — เร็วสุด, rate limit สูงสุด
    result = _binance_current_prices(ids, vs)
    missing = [cid for cid in ids if cid not in result]

    # 2) DeFiLlama — สำหรับเหรียญที่ไม่มีใน Binance
    if missing:
        llama = _llama_current_prices(missing, vs)
        result.update(llama)
        missing = [cid for cid in missing if cid not in result]

    # 3) CoinGecko — last resort
    if missing:
        cg = _cg_current_prices(missing, vs)
        result.update(cg)

    if not result:
        raise DataError(f"ไม่สามารถดึงราคาได้จากทุกแหล่ง: {ids}")
    return result


def history(coin_id: str, days: int = 30, vs: str = "usd") -> list[float]:
    """ราคาย้อนหลังของเหรียญเดียว -> list[price] เรียงตามเวลา.

    ลำดับ: Binance → DeFiLlama → CoinGecko
    """
    # 1) Binance klines
    result = _binance_history(coin_id, days, vs)

    # 2) DeFiLlama fallback
    if not result:
        result = _llama_history(coin_id, days, vs)

    # 3) CoinGecko last resort
    if not result:
        result = _cg_history(coin_id, days, vs)

    if not result:
        raise DataError(f"ไม่สามารถดึงราคา {coin_id} ย้อนหลัง {days} วัน")
    return result


def ohlc(coin_id: str, days: int = 30, vs: str = "usd") -> list[dict]:
    """OHLC ย้อนหลัง -> list[{ts, open, high, low, close}] เรียงตามเวลา.

    ใช้สำหรับ ATR และ Bollinger Bands.

    ลำดับ: Binance → CoinGecko (DeFiLlama ไม่มี OHLC)
    """
    # 1) Binance klines
    result = _binance_ohlc(coin_id, days, vs)

    # 2) CoinGecko fallback
    if not result:
        result = _cg_ohlc(coin_id, days, vs)

    if not result:
        raise DataError(f"ไม่สามารถดึง OHLC {coin_id} ย้อนหลัง {days} วัน")
    return result
