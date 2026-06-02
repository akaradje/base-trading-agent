"""Strategist (Planner) — Sonnet 4.6. ตั้งมุมมองตลาดรวม รันทุก ~30 นาที."""
from __future__ import annotations

import json
import time

SYSTEM = (
    "You are the Strategist agent in a crypto trading system for tokens on the Base chain. "
    "Given a market snapshot of several tokens (price, EMA trend, RSI), decide the overall "
    "market regime and a risk appetite for the next ~30 minutes. You do NOT place orders; you "
    "set guardrails the other agents operate within. Be conservative in choppy or downtrending "
    "markets. Respond ONLY via the structured schema."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "regime": {"type": "string", "enum": ["risk_on", "neutral", "risk_off"]},
        "risk_appetite": {
            "type": "number",
            "description": "0.0 = ห้ามเปิดไม้ใหม่, 1.0 = ลงเต็มที่ตามเพดานความเสี่ยง",
        },
        "allowed_symbols": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
    "required": ["regime", "risk_appetite", "allowed_symbols", "notes"],
    "additionalProperties": False,
}

DEFAULT = {
    "regime": "neutral",
    "risk_appetite": 0.5,
    "allowed_symbols": [],   # ว่าง = อนุญาตทุกเหรียญ (orchestrator ตีความ)
    "notes": "default (LLM ไม่พร้อม)",
}


class Strategist:
    def __init__(self, llm, cfg: dict):
        self.llm = llm
        self.cfg = cfg
        self.model = cfg.get("model", "claude-sonnet-4-6")
        self.effort = cfg.get("effort", "medium")
        self.refresh_sec = int(cfg.get("refresh_min", 30)) * 60
        self._last_ts = 0.0
        self._cached = dict(DEFAULT)

    def view(self, snapshots: dict[str, dict]) -> dict:
        """คืนมุมมองตลาดล่าสุด (ใช้ cache จนกว่าจะถึงรอบ refresh)."""
        if not self.cfg.get("enabled", True) or not self.llm.available:
            return self._cached
        if time.time() - self._last_ts < self.refresh_sec:
            return self._cached

        user = "Market snapshot:\n" + json.dumps(snapshots, ensure_ascii=False, indent=2)
        out = self.llm.decide(
            model=self.model, system=SYSTEM, user=user,
            schema=SCHEMA, effort=self.effort, max_tokens=900,
        )
        self._last_ts = time.time()
        if out:
            self._cached = out
        return self._cached
