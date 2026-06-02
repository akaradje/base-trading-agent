"""Agent State Broadcaster — ส่งสถานะ agent ไป Supabase Realtime สำหรับ Dashboard

ทำหน้าที่เป็น "ตัวกลาง" ระหว่าง backend (Python) กับ frontend (Next.js Dashboard)
ทุกครั้งที่ agent เปลี่ยนสถานะ → อัปเดต Supabase → Frontend subscribe รับทันที

**NON-BLOCKING**: ใช้ background thread + queue เพื่อไม่ให้ block deterministic risk engine

สถานะของแต่ละ agent:
  - idle:     ว่าง, พร้อมทำงาน
  - working:  กำลังทำภารกิจ
  - thinking: กำลังคิด/วิเคราะห์ (LLM กำลังประมวลผล)
  - error:    เกิดข้อผิดพลาด

Mood (ท่าทางตัวละคร):
  - neutral: ปกติ
  - happy:   พอใจ (กำไร, ตัดสินใจสำเร็จ)
  - worried: กังวล (ตลาดผันผวน, ข้อมูลไม่พอ)
  - angry:   ไม่พอใจ (ขาดทุน, error)
  - sleeping: หลับ (risk_off, ไม่มีสัญญาณ)

Degrade gracefully: ถ้าไม่มี Supabase config → ไม่ทำอะไร (ไม่ crash)
"""
from __future__ import annotations

import os
import queue
import threading
from datetime import datetime, timezone
from typing import Any


class AgentBroadcaster:
    """ส่ง agent state ไป Supabase Realtime — NON-BLOCKING.

    ใช้ background thread + queue เพื่อให้ bot main loop ไม่ถูก block
    ถ้า Supabase ช้าหรือล่ม → bot ยังทำงานต่อได้ปกติ
    """

    # Agent IDs — ตรงกับ supabase-schema.sql
    AGENTS = ("strategist", "analyst", "critic", "onchain", "risk", "engine")

    def __init__(self, cfg: dict):
        self.enabled = False
        self._client = None
        self._queue: queue.Queue = queue.Queue(maxsize=500)
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()

        supabase_url = cfg.get("supabase_url") or os.environ.get("SUPABASE_URL", "")
        supabase_key = cfg.get("supabase_key") or os.environ.get("SUPABASE_ANON_KEY", "")

        if supabase_url and supabase_key:
            try:
                from supabase import create_client
                self._client = create_client(supabase_url, supabase_key)
                self.enabled = True
                self._start_worker()
            except ImportError:
                pass  # supabase-py ไม่ได้ติดตั้ง

    def _start_worker(self) -> None:
        """เริ่ม background thread สำหรับส่ง state updates."""
        self._worker = threading.Thread(target=self._process_queue, daemon=True)
        self._worker.start()

    def _process_queue(self) -> None:
        """Background thread: ดึง state updates จาก queue แล้วส่งไป Supabase."""
        while not self._stop_event.is_set():
            try:
                # รอ item จาก queue (timeout 1s เพื่อเช็ค stop_event)
                item = self._queue.get(timeout=1.0)
                if item is None:
                    break

                table, data = item
                self._execute(table, data)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                continue

    def _execute(self, table: str, data: dict) -> None:
        """ส่งข้อมูลไป Supabase — เรียกจาก worker thread เท่านั้น."""
        if not self._client:
            return
        try:
            if table == "trades":
                self._client.table(table).insert(data).execute()
            else:
                self._client.table(table).upsert(data).execute()
        except Exception:
            pass  # broadcast failure ไม่ควรหยุด bot

    def _enqueue(self, table: str, data: dict) -> None:
        """เพิ่ม state update เข้า queue (non-blocking)."""
        if not self.enabled:
            return
        try:
            self._queue.put_nowait((table, data))
        except queue.Full:
            # Queue เต็ม → 丢弃 oldest item เพื่อให้ bot ไม่ block
            try:
                self._queue.get_nowait()
                self._queue.put_nowait((table, data))
            except (queue.Empty, queue.Full):
                pass

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ──────────────────────────────────────────────
    # Agent State Updates (Non-blocking)
    # ──────────────────────────────────────────────

    def update_agent(self, agent_id: str, status: str, task: str = "",
                     message: str = "", mood: str = "neutral",
                     metadata: dict | None = None) -> None:
        """อัปเดตสถานะ agent ไป Supabase (non-blocking)."""
        self._enqueue("agent_states", {
            "agent_id": agent_id,
            "status": status,
            "current_task": task,
            "bubble_message": message,
            "avatar_mood": mood,
            "last_action_ts": self._now(),
            "metadata": metadata or {},
        })

    def set_idle(self, agent_id: str, message: str = "") -> None:
        """ตั้งสถานะ idle (ว่าง)."""
        self.update_agent(agent_id, "idle", message=message, mood="neutral")

    def set_working(self, agent_id: str, task: str, message: str = "") -> None:
        """ตั้งสถานะ working (กำลังทำงาน)."""
        self.update_agent(agent_id, "working", task=task, message=message, mood="happy")

    def set_thinking(self, agent_id: str, message: str = "") -> None:
        """ตั้งสถานะ thinking (LLM กำลังประมวลผล)."""
        self.update_agent(agent_id, "thinking", message=message, mood="worried")

    def set_error(self, agent_id: str, message: str = "") -> None:
        """ตั้งสถานะ error (เกิดข้อผิดพลาด)."""
        self.update_agent(agent_id, "error", message=message, mood="angry")

    def set_sleeping(self, agent_id: str, message: str = "") -> None:
        """ตั้งสถานะ sleeping (ไม่มีสัญญาณ, risk_off)."""
        self.update_agent(agent_id, "idle", message=message, mood="sleeping")

    # ──────────────────────────────────────────────
    # Portfolio & Trade Updates (Non-blocking)
    # ──────────────────────────────────────────────

    def broadcast_portfolio(self, equity: float, cash: float, pnl_pct: float,
                            positions: int, trades_today: int) -> None:
        """อัปเดตข้อมูลพอร์ตไป Supabase (non-blocking)."""
        self._enqueue("portfolio_state", {
            "id": "main",
            "equity": round(equity, 2),
            "cash": round(cash, 2),
            "pnl_pct": round(pnl_pct, 4),
            "positions": positions,
            "trades_today": trades_today,
            "updated_at": self._now(),
        })

    def broadcast_trade(self, symbol: str, side: str, price: float,
                        qty: float, reason: str) -> None:
        """บันทึก trade ไป Supabase (non-blocking)."""
        self._enqueue("trades", {
            "symbol": symbol,
            "side": side,
            "price": round(price, 6),
            "qty": round(qty, 6),
            "reason": reason,
            "ts": self._now(),
        })

    # ──────────────────────────────────────────────
    # Bulk Operations
    # ──────────────────────────────────────────────

    def set_all_idle(self, message: str = "Waiting for next cycle") -> None:
        """ตั้งทุก agent เป็น idle พร้อมกัน (non-blocking)."""
        for agent_id in self.AGENTS:
            self.set_idle(agent_id, message)

    def set_all_sleeping(self, message: str = "Market is quiet") -> None:
        """ตั้งทุก agent เป็น sleeping (non-blocking)."""
        for agent_id in self.AGENTS:
            self.set_sleeping(agent_id, message)

    # ──────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────

    def shutdown(self) -> None:
        """หยุด worker thread อย่างสุภาพ."""
        self._stop_event.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=5)

    @property
    def queue_size(self) -> int:
        """จำนวน items ใน queue (สำหรับ monitoring)."""
        return self._queue.qsize()
