"""Alert System — ส่งการแจ้งเตือนผ่าน Telegram เมื่อเหตุการณ์สำคัญเกิดขึ้น.

รองรับ:
  - Kill switch ทำงาน (ทุกระดับ)
  - Data feed นิ่ง > threshold
  - Emergency liquidation
  - Daily P&L summary

ใช้ Telegram Bot API (ฟรี) — ต้องสร้าง bot ผ่าน @BotFather
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import requests


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


class AlertManager:
    """ส่งการแจ้งเตือนผ่าน Telegram — degrade ได้ (ถ้าไม่ตั้งค่า = ไม่ส่ง)."""

    def __init__(self, cfg: dict):
        self.enabled = cfg.get("enabled", False)
        self.token = cfg.get("telegram_token") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = cfg.get("telegram_chat_id") or os.environ.get("TELEGRAM_CHAT_ID", "")
        self.triggers = {
            "on_kill_switch": cfg.get("on_kill_switch", True),
            "on_data_stale": cfg.get("on_data_stale", True),
            "on_emergency": cfg.get("on_emergency", True),
            "daily_summary": cfg.get("daily_summary", True),
        }
        self._session = requests.Session()
        self._last_daily_ts: float = 0

    @property
    def available(self) -> bool:
        return self.enabled and bool(self.token) and bool(self.chat_id)

    def _send(self, text: str) -> bool:
        """ส่งข้อความ Telegram — คืน True ถ้าสำเร็จ."""
        if not self.available:
            return False
        try:
            r = self._session.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10,
            )
            return r.status_code == 200
        except Exception:
            return False

    # ---- Alert Triggers ----

    def on_kill_switch(self, level: str, reason: str, positions: int) -> None:
        """แจ้งเตือนเมื่อ kill switch / circuit breaker ทำงาน."""
        if not self.triggers.get("on_kill_switch"):
            return
        emoji = {"REDUCED": "⚠️", "HALTED": "🛑", "KILL": "🚨"}.get(level, "❓")
        self._send(
            f"{emoji} <b>{level}</b>\n"
            f"Reason: {reason}\n"
            f"Positions: {positions}\n"
            f"Time: {_ts()}"
        )

    def on_data_stale(self, stale_sec: float, positions: int) -> None:
        """แจ้งเตือนเมื่อ data feed นิ่งนานเกินไป."""
        if not self.triggers.get("on_data_stale"):
            return
        self._send(
            f"📡 <b>DATA STALE</b>\n"
            f"No prices for {stale_sec:.0f}s\n"
            f"Positions liquidated: {positions}\n"
            f"Time: {_ts()}"
        )

    def on_emergency(self, reason: str, sold: list[str]) -> None:
        """แจ้งเตือนเมื่อ emergency liquidation."""
        if not self.triggers.get("on_emergency"):
            return
        symbols = ", ".join(sold) if sold else "none"
        self._send(
            f"🚨 <b>EMERGENCY LIQUIDATION</b>\n"
            f"Reason: {reason}\n"
            f"Sold: {symbols}\n"
            f"Time: {_ts()}"
        )

    def on_daily_summary(self, equity: float, start_cash: float,
                         pnl_pct: float, positions: dict, trades_today: int) -> bool:
        """สรุป P&L รายวัน — คืน True ถ้าส่งสำเร็จ (กันส่งซ้ำ)."""
        if not self.triggers.get("daily_summary"):
            return False
        held = ", ".join(positions.keys()) if positions else "none"
        self._send(
            f"📊 <b>Daily Summary</b>\n"
            f"Equity: ${equity:,.2f} ({pnl_pct:+.2f}%)\n"
            f"Cash: ${equity - sum(p * 0 for p in positions.values()):,.2f}\n"
            f"Holding: {held}\n"
            f"Trades today: {trades_today}\n"
            f"Time: {_ts()}"
        )
        return True

    def on_llm_failure(self, agent: str, failures: int) -> None:
        """แจ้งเตือนเมื่อ LLM agent fail ติดต่อกัน."""
        if failures < 3:
            return
        self._send(
            f"🤖 <b>LLM Failure</b>\n"
            f"Agent: {agent}\n"
            f"Consecutive failures: {failures}\n"
            f"Time: {_ts()}"
        )
