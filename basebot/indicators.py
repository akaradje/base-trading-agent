"""Indicator แบบ pure-python (ไม่พึ่ง pandas) — EMA, RSI, helper สำหรับสัญญาณ crossover."""
from __future__ import annotations


def ema(prices: list[float], period: int) -> list[float]:
    """Exponential moving average. คืน list ความยาวเท่ากับ prices (ช่วง warmup ใช้ค่าเฉลี่ยสะสม)."""
    if not prices:
        return []
    k = 2 / (period + 1)
    out = [prices[0]]
    for p in prices[1:]:
        out.append(p * k + out[-1] * (1 - k))
    return out


def rsi(prices: list[float], period: int = 14) -> float | None:
    """RSI (Wilder smoothing). คืน None ถ้าข้อมูลไม่พอ. ช่วง 0-100."""
    if len(prices) < period + 1:
        return None
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        delta = prices[i] - prices[i - 1]
        gains += max(delta, 0.0)
        losses += max(-delta, 0.0)
    avg_gain, avg_loss = gains / period, losses / period

    for i in range(period + 1, len(prices)):
        delta = prices[i] - prices[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def crossover(fast: list[float], slow: list[float]) -> str:
    """ตรวจการตัดกันของเส้นเร็ว/ช้าในแท่งล่าสุด.

    คืน 'golden' (เร็วตัดขึ้น), 'death' (เร็วตัดลง), หรือ 'none'.
    """
    if len(fast) < 2 or len(slow) < 2:
        return "none"
    prev = fast[-2] - slow[-2]
    curr = fast[-1] - slow[-1]
    if prev <= 0 < curr:
        return "golden"
    if prev >= 0 > curr:
        return "death"
    return "none"


def snapshot(prices: list[float], cfg: dict,
             highs: list[float] | None = None,
             lows: list[float] | None = None,
             volumes: list[float] | None = None) -> dict:
    """รวม indicator ทั้งหมดของเหรียญหนึ่ง ณ จุดล่าสุด (ใช้ส่งต่อให้ strategy + agents).

    Phase 8: เพิ่ม MACD, ADX, MFI, Stochastic, volume data
    """
    fast_p = int(cfg.get("ema_fast", 12))
    slow_p = int(cfg.get("ema_slow", 26))
    rsi_p = int(cfg.get("rsi_period", 14))

    fast = ema(prices, fast_p)
    slow = ema(prices, slow_p)

    result = {
        "price": prices[-1] if prices else None,
        "ema_fast": round(fast[-1], 6) if fast else None,
        "ema_slow": round(slow[-1], 6) if slow else None,
        "rsi": rsi(prices, rsi_p),
        "cross": crossover(fast, slow),
        "trend_up": bool(fast and slow and fast[-1] > slow[-1]),
        "n_points": len(prices),
    }

    # MACD (ใช้ prices อย่างเดียว)
    macd_vals = macd(prices, fast_p, slow_p, 9)
    if macd_vals:
        result["macd"] = round(macd_vals[0], 6)
        result["macd_signal"] = round(macd_vals[1], 6)
        result["macd_hist"] = round(macd_vals[2], 6)
        result["macd_bullish"] = macd_vals[2] > 0

    # Bollinger Bands (ใช้ prices อย่างเดียว)
    bb_period = int(cfg.get("bb_period", 20))
    bb_std = float(cfg.get("bb_std", 2.0))
    bb = bollinger_bands(prices, bb_period, bb_std)
    if bb:
        result["bb_upper"] = round(bb[0], 6)
        result["bb_middle"] = round(bb[1], 6)
        result["bb_lower"] = round(bb[2], 6)
        result["bb_width"] = round((bb[0] - bb[2]) / bb[1] * 100, 2) if bb[1] > 0 else None

    # ใช้ OHLC data สำหรับ indicators ที่ต้อง high/low
    if highs and lows and len(highs) == len(prices) and len(lows) == len(prices):
        atr_period = int(cfg.get("atr_period", 14))
        atr_val = atr(highs, lows, prices, atr_period)
        if atr_val is not None:
            result["atr"] = round(atr_val, 6)
            result["atr_pct"] = round(atr_val / prices[-1] * 100, 2) if prices[-1] > 0 else None

        adx_period = int(cfg.get("adx_period", 14))
        adx_val = adx(highs, lows, prices, adx_period)
        if adx_val is not None:
            result["adx"] = round(adx_val, 2)
            result["adx_trend"] = adx_val > 25

        stoch_vals = stochastic(highs, lows, prices, 14, 3)
        if stoch_vals:
            result["stoch_k"] = round(stoch_vals[0], 2)
            result["stoch_d"] = round(stoch_vals[1], 2)

        # MFI ต้องมี volume ด้วย
        if volumes and len(volumes) == len(prices):
            mfi_val = mfi(highs, lows, prices, volumes, 14)
            if mfi_val is not None:
                result["mfi"] = round(mfi_val, 2)

    # Volume data
    if volumes and len(volumes) > 0:
        result["volume"] = volumes[-1]
        vol_avg = volume_sma(volumes, 20)
        if vol_avg and vol_avg > 0:
            result["volume_avg"] = round(vol_avg, 2)
            result["volume_ratio"] = round(volumes[-1] / vol_avg, 2)

    return result


def atr(highs: list[float], lows: list[float], closes: list[float],
        period: int = 14) -> float | None:
    """Average True Range (Wilder smoothing). คืน ATR ณ จุดล่าสุด หรือ None ถ้าข้อมูลไม่พอ.

    True Range = max(high-low, |high-prev_close|, |low-prev_close|)
    ATR = Wilder-smoothed average ของ True Range ตาม period
    """
    if len(closes) < 2 or len(highs) != len(closes) or len(lows) != len(closes):
        return None

    trs: list[float] = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)

    if len(trs) < period:
        return None

    # Wilder smoothing (เดียวกับ RSI)
    atr_val = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr_val = (atr_val * (period - 1) + tr) / period
    return atr_val


def bollinger_bands(prices: list[float], period: int = 20,
                    num_std: float = 2.0) -> tuple[float, float, float] | None:
    """Bollinger Bands ณ จุดล่าสุด. คืน (upper, middle, lower) หรือ None ถ้าข้อมูลไม่พอ."""
    if len(prices) < period:
        return None
    window = prices[-period:]
    middle = sum(window) / period
    variance = sum((p - middle) ** 2 for p in window) / period
    std = variance ** 0.5
    return (middle + num_std * std, middle, middle - num_std * std)


def macd(prices: list[float], fast: int = 12, slow: int = 26,
         signal: int = 9) -> tuple[float, float, float] | None:
    """MACD ณ จุดล่าสุด. คืน (macd_line, signal_line, histogram) หรือ None ถ้าข้อมูลไม่พอ.

    - macd_line = EMA(fast) - EMA(slow)
    - signal_line = EMA(macd_line, signal)
    - histogram = macd_line - signal_line
    """
    if len(prices) < slow + signal:
        return None
    fast_ema = ema(prices, fast)
    slow_ema = ema(prices, slow)
    macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
    signal_ema = ema(macd_line, signal)
    hist = macd_line[-1] - signal_ema[-1]
    return (macd_line[-1], signal_ema[-1], hist)


def adx(highs: list[float], lows: list[float], closes: list[float],
        period: int = 14) -> float | None:
    """Average Directional Index (Wilder smoothing). คืน ADX ณ จุดล่าสุด (0-100) หรือ None.

    ADX > 25 = strong trend, ADX < 20 = weak/no trend
    """
    if len(closes) < period * 2 + 1:
        return None

    plus_dm, minus_dm, tr_list = [], [], []
    for i in range(1, len(closes)):
        high_diff = highs[i] - highs[i - 1]
        low_diff = lows[i - 1] - lows[i]
        plus_dm.append(high_diff if high_diff > low_diff and high_diff > 0 else 0)
        minus_dm.append(low_diff if low_diff > high_diff and low_diff > 0 else 0)
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        tr_list.append(tr)

    # Wilder smoothing
    atr_val = sum(tr_list[:period]) / period
    plus_di_val = sum(plus_dm[:period]) / period
    minus_di_val = sum(minus_dm[:period]) / period

    dx_values = []
    for i in range(period, len(tr_list)):
        atr_val = (atr_val * (period - 1) + tr_list[i]) / period
        plus_di_val = (plus_di_val * (period - 1) + plus_dm[i]) / period
        minus_di_val = (minus_di_val * (period - 1) + minus_dm[i]) / period

        if atr_val == 0:
            continue
        plus_di = 100 * plus_di_val / atr_val
        minus_di = 100 * minus_di_val / atr_val
        di_sum = plus_di + minus_di
        if di_sum == 0:
            dx_values.append(0)
        else:
            dx_values.append(100 * abs(plus_di - minus_di) / di_sum)

    if len(dx_values) < period:
        return None

    adx_val = sum(dx_values[:period]) / period
    for dx in dx_values[period:]:
        adx_val = (adx_val * (period - 1) + dx) / period
    return adx_val


def mfi(highs: list[float], lows: list[float], closes: list[float],
        volumes: list[float], period: int = 14) -> float | None:
    """Money Flow Index (volume-weighted RSI). คืน MFI ณ จุดล่าสุด (0-100) หรือ None.

    MFI < 20 = oversold, MFI > 80 = overbought
    """
    if len(closes) < period + 1 or len(volumes) < period + 1:
        return None

    typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    money_flow = [tp * v for tp, v in zip(typical_prices, volumes)]

    pos_flow, neg_flow = 0.0, 0.0
    for i in range(1, period + 1):
        if typical_prices[i] > typical_prices[i - 1]:
            pos_flow += money_flow[i]
        else:
            neg_flow += money_flow[i]

    for i in range(period + 1, len(typical_prices)):
        if typical_prices[i] > typical_prices[i - 1]:
            pos_flow = (pos_flow * (period - 1) + money_flow[i]) / period
            neg_flow = (neg_flow * (period - 1)) / period
        else:
            neg_flow = (neg_flow * (period - 1) + money_flow[i]) / period
            pos_flow = (pos_flow * (period - 1)) / period

    if neg_flow == 0:
        return 100.0
    ratio = pos_flow / neg_flow
    return 100.0 - (100.0 / (1.0 + ratio))


def stochastic(highs: list[float], lows: list[float], closes: list[float],
               k_period: int = 14, d_period: int = 3) -> tuple[float, float] | None:
    """Stochastic oscillator. คืน (%K, %D) ณ จุดล่าสุด หรือ None.

    %K < 20 = oversold, %K > 80 = overbought
    %D = SMA ของ %K (signal line)
    """
    if len(closes) < k_period:
        return None

    k_values = []
    for i in range(k_period - 1, len(closes)):
        window_high = max(highs[i - k_period + 1:i + 1])
        window_low = min(lows[i - k_period + 1:i + 1])
        if window_high == window_low:
            k_values.append(50.0)
        else:
            k_values.append(100 * (closes[i] - window_low) / (window_high - window_low))

    if len(k_values) < d_period:
        return None

    k = k_values[-1]
    d = sum(k_values[-d_period:]) / d_period
    return (k, d)


def volume_sma(volumes: list[float], period: int = 20) -> float | None:
    """Simple Moving Average ของ volume. คืนค่าเฉลี่ย หรือ None ถ้าข้อมูลไม่พอ."""
    if len(volumes) < period:
        return None
    return sum(volumes[-period:]) / period
