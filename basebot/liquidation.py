"""Liquidation Cascade Detection — ตรวจจับ forced liquidations จาก Open Interest data.

สัญญาณ mean-reversion: เมื่อ OI ลดลงอย่างรวดเร็ว + ราคาเคลื่อนที่แรง
→ มี forced liquidation เกิดขึ้น → โอกาส mean-reversion entry

สัญญาณ 2 ชนิด:
  1. Long Cascade: OI ลด + ราคาลง = forced long liquidations → อาจ rebound
  2. Short Cascade: OI ลด + ราคาขึ้น = forced short liquidations → อาจ pullback

Data source: Binance Futures API (public, ไม่ต้องมี API key)
  - Open Interest: GET /fapi/v1/openInterest
  - OI History: GET /futures/data/openInterestHist
"""
from __future__ import annotations

import time

import requests

_session = requests.Session()
_session.headers.update({"User-Agent": "base-trading-agent/0.1"})


def _get_json(url: str, params: dict | None = None, timeout: int = 15) -> dict | list | None:
    """GET JSON with basic error handling."""
    try:
        r = _session.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ──────────────────────────────────────────────
# Open Interest Data
# ──────────────────────────────────────────────

# CoinGecko ID -> Binance Futures symbol mapping
_COINGECKO_TO_BINANCE: dict[str, str] = {
    "ethereum": "ETHUSDT",
    "aerodrome-finance": "AEROUSDT",
    "degen-base": "DEGENUSDT",
}


def get_oi_history(symbol: str = "ETHUSDT", period: str = "5m",
                   limit: int = 100) -> list[dict] | None:
    """ดึง Open Interest history จาก Binance Futures.

    คืน list of {"ts": timestamp_ms, "oi": float, "oi_value": float}
    หรือ None ถ้า API ไม่ตอบ
    """
    data = _get_json(
        "https://fapi.binance.com/futures/data/openInterestHist",
        {"symbol": symbol, "period": period, "limit": limit},
    )
    if not data or not isinstance(data, list):
        return None

    result = []
    for item in data:
        try:
            result.append({
                "ts": int(item.get("timestamp", 0)),
                "oi": float(item.get("sumOpenInterest", 0)),
                "oi_value": float(item.get("sumOpenInterestValue", 0)),
            })
        except (ValueError, TypeError):
            continue
    return result if len(result) >= 10 else None


def get_current_oi(symbol: str = "ETHUSDT") -> float | None:
    """ดึง Open Interest ปัจจุบันจาก Binance Futures."""
    data = _get_json(
        "https://fapi.binance.com/fapi/v1/openInterest",
        {"symbol": symbol},
    )
    if not data:
        return None
    try:
        return float(data.get("openInterest", 0))
    except (ValueError, TypeError):
        return None


# ──────────────────────────────────────────────
# Cascade Detection
# ──────────────────────────────────────────────

def detect_cascade(oi_history: list[dict], price_history: list[float],
                   lookback: int = 60, threshold_pct: float = 5.0,
                   price_threshold_pct: float = 2.0) -> str | None:
    """ตรวจจับ liquidation cascade จาก OI และ price history.

    Args:
        oi_history: list of {"ts", "oi", "oi_value"} — เรียงจากเก่าไปใหม่
        price_history: list of prices — เรียงจากเก่าไปใหม่
        lookback: จำนวนจุดย้อนหลังที่ใช้เปรียบเทียบ
        threshold_pct: % change ของ OI ที่ถือว่า significant
        price_threshold_pct: % change ของราคาที่ถือว่า significant

    Returns:
        "long_cascade"  — OI ลด + ราคาลง = forced long liquidations (mean-reversion long)
        "short_cascade" — OI ลด + ราคาขึ้น = forced short liquidations (mean-reversion short)
        None — ไม่มี cascade
    """
    if len(oi_history) < lookback or len(price_history) < lookback:
        return None

    # ใช้ค่าเฉลี่ย 5 จุดล่าสุด vs 5 จุดย้อนหลัง เพื่อลด noise
    recent_oi = [d["oi"] for d in oi_history[-5:]]
    older_oi = [d["oi"] for d in oi_history[-lookback:-lookback + 5]]

    recent_price = price_history[-5:]
    older_price = price_history[-lookback:-lookback + 5]

    if not recent_oi or not older_oi or not recent_price or not older_price:
        return None

    avg_recent_oi = sum(recent_oi) / len(recent_oi)
    avg_older_oi = sum(older_oi) / len(older_oi)
    avg_recent_price = sum(recent_price) / len(recent_price)
    avg_older_price = sum(older_price) / len(older_price)

    if avg_older_oi <= 0 or avg_older_price <= 0:
        return None

    oi_change_pct = (avg_recent_oi - avg_older_oi) / avg_older_oi * 100
    price_change_pct = (avg_recent_price - avg_older_price) / avg_older_price * 100

    # Long cascade: OI ลด + ราคาลง = forced long liquidations
    if oi_change_pct < -threshold_pct and price_change_pct < -price_threshold_pct:
        return "long_cascade"

    # Short cascade: OI ลด + ราคาขึ้น = forced short liquidations
    if oi_change_pct < -threshold_pct and price_change_pct > price_threshold_pct:
        return "short_cascade"

    return None


# ──────────────────────────────────────────────
# Liquidation Signal Agent
# ──────────────────────────────────────────────

class LiquidationDetector:
    """ตรวจจับ liquidation cascade สำหรับทุกเหรียญที่เทรด.

    ไม่ใช้ LLM — ทำงาน deterministic จาก Binance Futures data
    ส่งสัญญาณ mean-reversion ให้ orchestrator
    """

    def __init__(self, cfg: dict | None = None):
        cfg = cfg or {}
        self.lookback = int(cfg.get("lookback", 60))
        self.oi_threshold = float(cfg.get("oi_threshold_pct", 5.0))
        self.price_threshold = float(cfg.get("price_threshold_pct", 2.0))
        self._cache: dict[str, dict] = {}
        self._cache_ts: float = 0
        self._cache_ttl = 300  # 5 นาที

    def scan(self, coin_ids: list[str],
             price_histories: dict[str, list[float]]) -> dict[str, dict]:
        """สแกนทุกเหรียญหา liquidation cascade.

        Args:
            coin_ids: list of CoinGecko IDs (เช่น ["ethereum", "aerodrome-finance"])
            price_histories: {coin_id: [prices...]} — ราคาเรียงจากเก่าไปใหม่

        Returns:
            {coin_id: {"cascade": "long_cascade"|"short_cascade"|None,
                       "oi_change_pct": float, "price_change_pct": float,
                       "summary": str}}
        """
        now = time.time()
        if now - self._cache_ts < self._cache_ttl and self._cache:
            return self._cache

        results = {}
        for cid in coin_ids:
            binance_sym = _COINGECKO_TO_BINANCE.get(cid)
            if not binance_sym:
                results[cid] = {"cascade": None, "summary": f"{cid}: no Binance mapping"}
                continue

            oi_data = get_oi_history(binance_sym, period="5m", limit=self.lookback + 10)
            prices = price_histories.get(cid, [])

            if not oi_data or len(prices) < self.lookback:
                results[cid] = {"cascade": None, "summary": f"{cid}: insufficient data"}
                continue

            cascade = detect_cascade(
                oi_data, prices,
                lookback=self.lookback,
                threshold_pct=self.oi_threshold,
                price_threshold_pct=self.price_threshold,
            )

            # คำนวณ % change สำหรับ log
            recent_oi = [d["oi"] for d in oi_data[-5:]]
            older_oi = [d["oi"] for d in oi_data[-self.lookback:-self.lookback + 5]]
            oi_change = 0.0
            if recent_oi and older_oi and sum(older_oi) > 0:
                oi_change = (sum(recent_oi) / len(recent_oi) -
                             sum(older_oi) / len(older_oi)) / (sum(older_oi) / len(older_oi)) * 100

            recent_px = prices[-5:]
            older_px = prices[-self.lookback:-self.lookback + 5]
            price_change = 0.0
            if recent_px and older_px and sum(older_px) > 0:
                price_change = (sum(recent_px) / len(recent_px) -
                                sum(older_px) / len(older_px)) / (sum(older_px) / len(older_px)) * 100

            summary_parts = [f"OI={oi_change:+.1f}%", f"price={price_change:+.1f}%"]
            if cascade:
                summary_parts.append(f"⚠️ {cascade}")
            summary = ", ".join(summary_parts)

            results[cid] = {
                "cascade": cascade,
                "oi_change_pct": round(oi_change, 2),
                "price_change_pct": round(price_change, 2),
                "summary": summary,
            }

        self._cache = results
        self._cache_ts = now
        return results
