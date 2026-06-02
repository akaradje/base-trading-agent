"""Dataset Preparation — แปลง training data เป็น format สำหรับ LoRA fine-tuning.

อ่าน decisions.jsonl + outcomes.jsonl → สร้าง training pairs:
  - Input: indicators + regime + onchain signals
  - Target: action + conviction + rationale (จาก decisions ที่ผลลัพธ์ดี)

กรองเฉพาะ decisions ที่:
  1. มี outcome แล้ว (ขายแล้ว)
  2. ผลลัพธ์ดี (กำไร) — ให้โมเดลเรียนจาก decisions ที่ถูกต้อง

Output: JSONL file ที่พร้อมใช้ fine-tune
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent.parent


def load_decisions(path: str | Path) -> list[dict]:
    """โหลด decisions จาก JSONL file."""
    path = Path(path)
    if not path.exists():
        return []
    decisions = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    decisions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return decisions


def load_outcomes(path: str | Path) -> list[dict]:
    """โหลด outcomes จาก JSONL file."""
    return load_decisions(path)  # same format


def build_training_pairs(decisions_path: str | Path,
                         outcomes_path: str | Path,
                         min_pnl: float = 0.0,
                         include_losses: bool = False) -> list[dict]:
    """สร้าง training pairs จาก decisions + outcomes.

    Args:
        decisions_path: path ไป decisions.jsonl
        outcomes_path: path ไป outcomes.jsonl
        min_pnl: minimum PnL% ที่จะรวม (default 0 = เฉพาะกำไร)
        include_losses: รวม decisions ที่ขาดทุนด้วย (label เป็น "negative example")

    Returns:
        list of training pairs:
        [
            {
                "instruction": "Analyze this crypto trading scenario...",
                "input": "<indicators + regime + onchain>",
                "output": "<action + conviction + rationale>"
            },
            ...
        ]
    """
    decisions = load_decisions(decisions_path)
    outcomes = load_outcomes(outcomes_path)

    # สร้าง outcome lookup: symbol -> latest outcome
    outcome_map: dict[str, dict] = {}
    for outcome in outcomes:
        sym = outcome.get("symbol", "")
        outcome_map[sym] = outcome

    pairs = []
    for decision in decisions:
        sym = decision.get("symbol", "")
        action = decision.get("action", "hold")

        # ข้าม hold decisions (ไม่มีประโยชน์สำหรับ training)
        if action == "hold":
            continue

        # หา outcome ที่ตรงกัน
        outcome = outcome_map.get(sym)
        if not outcome:
            continue

        pnl = outcome.get("pnl_pct", 0)
        correct = outcome.get("correct", False)

        # กรองตาม PnL threshold
        if not include_losses and pnl < min_pnl:
            continue

        # สร้าง instruction
        instruction = (
            "You are a crypto trading analyst for Base chain tokens. "
            "Analyze the following trading scenario and decide: action (buy/sell/reduce/hold), "
            "conviction (0-1), and rationale. Consider momentum, volatility, and market regime."
        )

        # สร้าง input (ไม่รวม action/conviction — ให้โมเดลทำนาย)
        input_data = {
            "symbol": sym,
            "price": decision.get("price"),
            "indicators": decision.get("indicators", {}),
            "regime": decision.get("regime", {}),
            "onchain": decision.get("onchain", {}),
            "cascade": decision.get("cascade", {}),
        }

        # สร้าง output (คำตอบที่ถูกต้อง)
        output_data = {
            "action": action,
            "conviction": decision.get("conviction", 0),
            "rationale": decision.get("rationale", ""),
        }

        # ถ้าเป็น negative example เพิ่มผลลัพธ์
        if include_losses and not correct:
            output_data["note"] = f"INCORRECT: resulted in {pnl:+.2f}% PnL"
            output_data["correct_action"] = "hold" if action == "buy" else "buy"

        pairs.append({
            "instruction": instruction,
            "input": json.dumps(input_data, ensure_ascii=False),
            "output": json.dumps(output_data, ensure_ascii=False),
        })

    return pairs


def export_for_finetune(pairs: list[dict], output_path: str | Path) -> int:
    """ส่งออก training pairs เป็น JSONL file สำหรับ fine-tune.

    Format: {"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for pair in pairs:
            messages = {
                "messages": [
                    {"role": "system", "content": pair["instruction"]},
                    {"role": "user", "content": pair["input"]},
                    {"role": "assistant", "content": pair["output"]},
                ]
            }
            f.write(json.dumps(messages, ensure_ascii=False) + "\n")
            count += 1

    return count


def prepare_dataset(state_dir: str | Path | None = None,
                    output_path: str | Path | None = None,
                    min_pnl: float = 0.0,
                    include_losses: bool = True) -> dict:
    """เตรียม dataset จาก training data ที่เก็บไว้.

    ใช้จาก CLI: python -m basebot.training.dataset

    Returns:
        {"pairs": int, "output": str, "stats": {...}}
    """
    state_dir = Path(state_dir) if state_dir else ROOT / "state" / "training"
    output_path = Path(output_path) if output_path else state_dir / "finetune_dataset.jsonl"

    decisions_path = state_dir / "decisions.jsonl"
    outcomes_path = state_dir / "outcomes.jsonl"

    pairs = build_training_pairs(decisions_path, outcomes_path,
                                 min_pnl=min_pnl, include_losses=include_losses)
    count = export_for_finetune(pairs, output_path)

    return {
        "pairs": count,
        "output": str(output_path),
        "decisions": len(load_decisions(decisions_path)),
        "outcomes": len(load_outcomes(outcomes_path)),
    }


if __name__ == "__main__":
    import sys
    result = prepare_dataset()
    print(f"Dataset prepared: {result['pairs']} training pairs")
    print(f"  Decisions: {result['decisions']}")
    print(f"  Outcomes: {result['outcomes']}")
    print(f"  Output: {result['output']}")
