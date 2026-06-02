"""Training Data Collector — เก็บข้อมูล decision + outcome สำหรับ LoRA fine-tuning.

บันทึกทุกการตัดสินใจของ Analyst agent พร้อมผลลัพธ์ (กำไร/ขาดทุน)
เพื่อสร้าง training dataset สำหรับ fine-tune LLM ให้ตัดสินใจได้ดีขึ้น

ข้อมูลที่เก็บ:
  - Input: indicators, recent prices, regime, on-chain signals
  - Output: action, conviction, rationale
  - Outcome: pnl_pct (กำไร/ขาดทุนจริงหลังขาย)

บันทึกเป็น JSONL format — 1 line ต่อ 1 decision
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent.parent


class TrainingCollector:
    """เก็บ trading decisions สำหรับ fine-tuning dataset."""

    def __init__(self, output_dir: str | Path | None = None):
        self.output_dir = Path(output_dir) if output_dir else ROOT / "state" / "training"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._pending: dict[str, dict] = {}  # trade_id -> decision data

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def log_decision(self, symbol: str, price: float, action: str,
                     conviction: float, rationale: str,
                     indicators: dict, regime: dict,
                     onchain: dict | None = None,
                     cascade: dict | None = None,
                     analyst_output: dict | None = None) -> str:
        """บันทึกการตัดสินใจของ Analyst (ก่อนรู้ผลลัพธ์).

        คืน decision_id สำหรับเชื่อมกับ outcome ตอนขาย
        """
        decision_id = f"{symbol}_{int(time.time() * 1000)}"
        entry = {
            "decision_id": decision_id,
            "ts": self._now(),
            "symbol": symbol,
            "price": price,
            "action": action,
            "conviction": conviction,
            "rationale": rationale,
            "indicators": indicators,
            "regime": regime,
            "onchain": onchain or {},
            "cascade": cascade or {},
            "analyst_output": analyst_output or {},
            "outcome": None,  # จะเติมตอนขาย
        }

        # เขียนลง JSONL
        filepath = self.output_dir / "decisions.jsonl"
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # เก็บ pending สำหรับเชื่อม outcome
        if action == "buy":
            self._pending[decision_id] = entry

        return decision_id

    def log_outcome(self, symbol: str, entry_price: float, exit_price: float,
                    pnl_pct: float, hold_duration_min: float,
                    exit_reason: str) -> None:
        """บันทึกผลลัพธ์เมื่อขาย — อัปเดต decision ที่ pending.

        Args:
            symbol: ชื่อเหรียญ
            entry_price: ราคาเข้า
            exit_price: ราคาออก
            pnl_pct: กำไร/ขาดทุน (%)
            hold_duration_min: ระยะเวลาถือ (นาที)
            exit_reason: เหตุผลที่ขาย
        """
        # หา decision ที่ pending สำหรับ symbol นี้
        matching_id = None
        for did, entry in self._pending.items():
            if entry.get("symbol") == symbol:
                matching_id = did
                break

        outcome = {
            "ts": self._now(),
            "symbol": symbol,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl_pct": round(pnl_pct, 4),
            "hold_duration_min": round(hold_duration_min, 1),
            "exit_reason": exit_reason,
            "correct": pnl_pct > 0,  # กำไร = ตัดสินใจถูก
        }

        # เขียน outcome ลง JSONL แยก
        filepath = self.output_dir / "outcomes.jsonl"
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(outcome, ensure_ascii=False) + "\n")

        # ลบจาก pending
        if matching_id:
            del self._pending[matching_id]

    def get_stats(self) -> dict:
        """ดูสถิติ training data ที่เก็บแล้ว."""
        decisions_file = self.output_dir / "decisions.jsonl"
        outcomes_file = self.output_dir / "outcomes.jsonl"

        decisions_count = 0
        outcomes_count = 0
        correct_count = 0

        if decisions_file.exists():
            with open(decisions_file, encoding="utf-8") as f:
                decisions_count = sum(1 for _ in f)

        if outcomes_file.exists():
            with open(outcomes_file, encoding="utf-8") as f:
                for line in f:
                    outcomes_count += 1
                    try:
                        outcome = json.loads(line)
                        if outcome.get("correct"):
                            correct_count += 1
                    except json.JSONDecodeError:
                        continue

        return {
            "decisions": decisions_count,
            "outcomes": outcomes_count,
            "correct": correct_count,
            "accuracy": round(correct_count / outcomes_count, 4) if outcomes_count > 0 else 0,
            "pending": len(self._pending),
            "output_dir": str(self.output_dir),
        }
