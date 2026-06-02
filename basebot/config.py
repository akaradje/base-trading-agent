"""โหลดและตรวจ config.yaml + environment."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Symbol:
    id: str          # CoinGecko coin id เช่น "ethereum"
    name: str        # ticker ที่แสดงผล เช่น "ETH"


@dataclass
class Config:
    raw: dict[str, Any]
    mode: str
    poll_interval_sec: int
    base_currency: str
    starting_cash: float
    warmup_days: int
    symbols: list[Symbol]
    strategy: dict[str, Any]
    risk: dict[str, Any]
    agents: dict[str, Any]
    live: dict[str, Any]
    onchain: dict[str, Any]
    alerts: dict[str, Any]

    @property
    def agents_enabled(self) -> bool:
        # ชั้น LLM ทำงานได้ก็ต่อเมื่อเปิดใน config และมี OpenRouter API key
        return bool(self.agents.get("enabled")) and bool(os.environ.get("OPENROUTER_API_KEY"))

    @property
    def live_enabled(self) -> bool:
        # โหมด live ทำงานได้ก็ต่อเมื่อ mode=live และตั้งค่า live section ครบ
        return self.mode == "live" and bool(self.live.get("rpc_url"))

    def agent(self, name: str) -> dict[str, Any]:
        return self.agents.get(name, {}) or {}


def load_config(path: str | os.PathLike[str] | None = None) -> Config:
    path = Path(path) if path else ROOT / "config.yaml"
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    data = raw.get("data", {}) or {}
    symbols = [Symbol(id=s["id"], name=s.get("name", s["id"])) for s in raw.get("symbols", [])]
    if not symbols:
        raise ValueError("config.yaml: ต้องมีอย่างน้อย 1 เหรียญใน 'symbols'")

    return Config(
        raw=raw,
        mode=raw.get("mode", "paper"),
        poll_interval_sec=int(raw.get("poll_interval_sec", 60)),
        base_currency=raw.get("base_currency", "usd"),
        starting_cash=float(raw.get("starting_cash", 10_000)),
        warmup_days=int(data.get("warmup_days", 30)),
        symbols=symbols,
        strategy=raw.get("strategy", {}) or {},
        risk=raw.get("risk", {}) or {},
        agents=raw.get("agents", {}) or {},
        live=raw.get("live", {}) or {},
        onchain=raw.get("onchain", {}) or {},
        alerts=raw.get("alerts", {}) or {},
    )
