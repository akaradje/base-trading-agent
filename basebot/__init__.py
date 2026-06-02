"""Base Trading Agent — paper-trading bot สำหรับเหรียญบน Base.

โครงสร้าง:
  config      โหลด/ตรวจ config.yaml
  data        ดึงราคา (CoinGecko)
  indicators  EMA / RSI (pure python)
  strategy    แปลงราคา -> สัญญาณ BUY/SELL/HOLD
  portfolio   พอร์ตจำลอง เงินสด/โพซิชัน/PnL
  risk        stop-loss / take-profit / kill switch
  executor    PaperExecutor (ตอนนี้) + LiveExecutor stub (ต่อ Base ทีหลัง)
  engine      ลูปเทรด 24 ชม.
  backtest    ทดสอบกลยุทธ์กับข้อมูลย้อนหลัง
"""

__version__ = "0.1.0"
