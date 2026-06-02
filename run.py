#!/usr/bin/env python
"""จุดเริ่มต้นของ Base Trading Agent.

ใช้งาน:
  python run.py run                  # เปิดบอท paper trading 24 ชม. (Ctrl+C เพื่อหยุด)
  python run.py backtest --days 90   # ทดสอบกลยุทธ์ฐานกับข้อมูลย้อนหลัง
  python run.py status               # ดูสถานะพอร์ตล่าสุด
  python run.py health               # เช็คสถานะ health (heartbeat)
"""
from __future__ import annotations

import argparse
import io
import sys

# บังคับ stdout เป็น UTF-8 สำหรับ Windows (ป้องกัน UnicodeEncodeError กับอักขระไทย/emoji)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from basebot.config import load_config


def cmd_run(args):
    from basebot.engine import Engine
    from basebot.logging import setup_logging

    cfg = load_config(args.config)
    logger = setup_logging()

    # --mode override จาก CLI (แทนค่าใน config.yaml)
    if args.mode:
        cfg.mode = args.mode

    # ตรวจสอบความปลอดภัยเมื่อเข้าสู่ live mode
    if cfg.mode == "live":
        dry_run = cfg.live.get("dry_run", True)
        if dry_run:
            logger.warning("โหมด LIVE-DRY: จำลองธุรกรรมผ่าน Base MCP (ไม่ส่งจริง)")
        else:
            logger.error("คำเตือน: คุณกำลังเข้าสู่โหมด LIVE TRADING — เงินจริง!")
            print("   ทุกธุรกรรมจะถูกส่งไปยัง Base mainnet")
            confirm = input("   พิมพ์ YES เพื่อยืนยัน: ").strip()
            if confirm != "YES":
                logger.info("ยกเลิก — ไม่ได้เริ่ม live trading")
                return

    Engine(cfg, log=logger.info).run()


def cmd_backtest(args):
    from basebot.backtest import run_backtest
    cfg = load_config(args.config)
    print(f"=== Backtest {args.days} วัน ===")
    run_backtest(cfg, days=args.days)


def cmd_status(args):
    from basebot.portfolio import Portfolio
    cfg = load_config(args.config)
    mode = cfg.mode
    if mode == "live":
        dry = cfg.live.get("dry_run", True)
        mode = "live-dry" if dry else "live (!)"
    print(f"โหมด: {mode}")
    pf = Portfolio.load(cfg.starting_cash, float(cfg.risk.get("fee_pct", 0.003)))
    print(f"เงินสด: ${pf.cash:,.2f} | เริ่มต้น: ${pf.start_cash:,.2f}")
    print(f"จำนวนเทรดสะสม: {len(pf.trades)}")
    if pf.positions:
        print("โพซิชันที่ถือ:")
        for sym, pos in pf.positions.items():
            print(f"  {sym}: qty={pos.qty:.6f} @ entry={pos.entry_price:.4f}")
    else:
        print("ไม่มีโพซิชันที่ถืออยู่")
    for t in pf.trades[-5:]:
        print(f"  {t.ts[:19]} {t.side:4} {t.symbol} qty={t.qty:.4f} @ {t.price:.4f} ({t.reason})")


def cmd_health(args):
    from basebot.engine import Engine
    cfg = load_config(args.config)
    heartbeat_path = cfg.raw.get("heartbeat_path", "state/heartbeat.json")
    max_age = int(args.max_age) if args.max_age else cfg.poll_interval_sec * 5

    result = Engine.check_health(heartbeat_path, max_age)

    status_icon = {"ok": "✅", "degraded": "⚠️", "stale": "🔴", "missing": "❓", "error": "❌"}
    icon = status_icon.get(result["status"], "❓")

    print(f"{icon} Status: {result['status']}")
    print(f"   Healthy: {result['healthy']}")
    print(f"   Age: {result['age_sec']:.0f}s")
    print(f"   Cycles: {result['cycle_count']}")
    print(f"   Message: {result['message']}")

    sys.exit(0 if result["healthy"] else 1)


def main(argv=None):
    p = argparse.ArgumentParser(description="Base Trading Agent")
    p.add_argument("--config", default=None, help="path to config.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="เปิดบอท 24 ชม.")
    run_p.add_argument("--mode", choices=["paper", "live"], default=None,
                       help="override โหมด (paper/live) แทนค่าใน config.yaml")
    run_p.set_defaults(func=cmd_run)
    bt = sub.add_parser("backtest", help="ทดสอบย้อนหลัง")
    bt.add_argument("--days", type=int, default=90)
    bt.set_defaults(func=cmd_backtest)
    sub.add_parser("status", help="ดูสถานะพอร์ต").set_defaults(func=cmd_status)
    health_p = sub.add_parser("health", help="เช็คสถานะ health (heartbeat)")
    health_p.add_argument("--max-age", type=int, default=None,
                          help="max age ของ heartbeat (วินาที) — default: 5x poll_interval")
    health_p.set_defaults(func=cmd_health)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
