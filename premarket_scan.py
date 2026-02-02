# premarket_scan.py
# 盤前掃描：昨日 VWAP 趨勢 + 盤前價格 + 期權流動性 + Telegram 匯出

import sys
import json
import traceback
import os
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from telegram_utils import send_telegram_message


# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def get_last_trading_day_vwap(symbol, interval="5m"):
    """抓過去 7 天內最近一個完整交易日的 VWAP 狀態"""
    date = datetime.now().date()

    for i in range(1, 8):
        target_date = date - timedelta(days=i)
        start_str = target_date.strftime("%Y-%m-%d")
        end_str = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")

        try:
            df = yf.download(
                symbol,
                interval=interval,
                start=start_str,
                end=end_str,
                progress=False,
            )
            if df.empty or len(df) < 10:
                continue

            # 欄位處理
            if isinstance(df.columns, pd.MultiIndex):
                close_col = ("Close", symbol)
                high_col = ("High", symbol)
                low_col = ("Low", symbol)
                vol_col = ("Volume", symbol)
            else:
                close_col = "Close"
                high_col = "High"
                low_col = "Low"
                vol_col = "Volume"

            if vol_col not in df.columns:
                continue

            high, low, vol = df[high_col], df[low_col], df[vol_col]
            tp = (high + low) / 2.0
            pv = tp * vol
            vwap = pv.sum() / vol.sum()

            close = float(df[close_col].iloc[-1])
            pct = (close - vwap) / vwap * 100.0

            if pct > 0.3:
                trend = "Bullish"
            elif pct < -0.3:
                trend = "Bearish"
            else:
                trend = "Neutral"

            return {
                "date": start_str,
                "prev_close": close,
                "prev_vwap": float(vwap),
                "prev_trend": trend,
            }
        except Exception:
            continue

    return None


def get_premarket_data(symbol):
    """抓盤前價格：優先用 preMarketPrice，否則退回 fast_info.last_price"""
    try:
        tick = yf.Ticker(symbol)

        # 先試著從完整 info 抓 preMarketPrice（可能會比較慢）
        pre_price = None
        try:
            info_full = tick.info
            pre_price = info_full.get("preMarketPrice")
        except Exception:
            pre_price = None

        fast = tick.fast_info
        last_price = fast.last_price
        prev_close = fast.previous_close

        if not prev_close:
            return None

        # 判斷實際使用哪一個價格
        if pre_price is not None and pre_price > 0:
            price = float(pre_price)
            source = "preMarketPrice"
        else:
            # 退回最新價格（可能是盤中/盤後/盤前）
            if not last_price:
                return None
            price = float(last_price)
            source = "last_price"

        change_pct = (price - prev_close) / prev_close * 100.0

        return {
            "price": price,
            "prev_close": float(prev_close),
            "gap_pct": float(change_pct),
            "source": source,  # 額外標註來源
        }
    except Exception:
        return None


def get_options_score(symbol):
    """簡易期權流動性評分 (0-3分)"""
    try:
        tick = yf.Ticker(symbol)
        if not tick.options:
            return 0

        # 最近一個到期日
        chain = tick.option_chain(tick.options[0])
        calls = chain.calls

        price = tick.fast_info.last_price
        if not price:
            return 0

        # 只看 ATM 附近
        calls = calls[
            (calls["strike"] >= price * 0.95)
            & (calls["strike"] <= price * 1.05)
        ]
        vol = calls["volume"].sum()

        if vol > 5000:
            return 3
        if vol > 1000:
            return 2
        if vol > 100:
            return 1
        return 0
    except Exception:
        return 0


def decide_scenario(total_score: int) -> str:
    """
    暫時用 total_score 粗略映射 Scenario，之後你可以改成
    依 StockScore / IV / OI 的完整規則。
    """
    if total_score >= 6:
        return "A"
    if total_score <= 2:
        return "C"
    return "B"


# ---------------------------------------------------------
# Main Logic
# ---------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python premarket_scan.py SYMBOLS")
        sys.exit(1)

    symbols = [s.strip().upper() for s in sys.argv[1].split(",") if s.strip()]
    results = []

    print(f"Scanning {len(symbols)} symbols...")
    for sym in symbols:
        try:
            # 1. 昨日 VWAP 趨勢
            prev = get_last_trading_day_vwap(sym) or {
                "prev_trend": "N/A",
                "prev_close": 0.0,
            }

            # 2. 盤前價 / GAP
            pre = get_premarket_data(sym)
            if not pre:
                pre = {
                    "price": prev["prev_close"],
                    "prev_close": prev["prev_close"],
                    "gap_pct": 0.0,
                    "source": "fallback",
                }

            # 3. 期權簡易流動性分
            opt_score = get_options_score(sym)

            # 4. 打分邏輯（你之後可以改成更細）
            total_score = opt_score

            if abs(pre["gap_pct"]) > 1.5:
                total_score += 2
            elif abs(pre["gap_pct"]) > 0.5:
                total_score += 1

            if prev["prev_trend"] == "Bullish" and pre["gap_pct"] > 0:
                total_score += 1
            if prev["prev_trend"] == "Bearish" and pre["gap_pct"] < 0:
                total_score += 1

            scenario = decide_scenario(total_score)

            row = {
                "symbol": sym,
                "prev_trend": prev["prev_trend"],
                "prev_close": float(pre["prev_close"]),
                "price": float(pre["price"]),
                "gap_pct": float(pre["gap_pct"]),
                "opt_score": int(opt_score),
                "total_score": int(total_score),
                "scenario": scenario,
                "pre_source": pre.get("source", "unknown"),
            }

            results.append(row)
            print(
                f" - {sym}: prev_trend={row['prev_trend']}, "
                f"gap={row['gap_pct']:+.2f}%, opt={opt_score}, "
                f"score={total_score}, scenario={scenario}, "
                f"src={row['pre_source']}"
            )

        except Exception as e:
            print(f"Error {sym}: {e}")
            traceback.print_exc()

    # 輸出 JSON
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs("data", exist_ok=True)
    out_path = f"data/premarket_{today}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved premarket scan to {out_path}")

    # 發送 Telegram 摘要（全部 symbols，依 total_score 排序）
    if results:
        sorted_res = sorted(results, key=lambda x: x["total_score"], reverse=True)

        lines = [f"*Premarket Scan {today}*"]
        lines.append("`Ticker  Scen  Prev  Px   Δ%    Opt  Score`")
        for r in sorted_res:
            lines.append(
                f"{r['symbol']:>5}  {r['scenario']:<4}  "
                f"{r['prev_trend'][:4]:>4}  "
                f"{r['price']:>6.2f}  {r['gap_pct']:+5.2f}%  "
                f"{r['opt_score']:>3}   {r['total_score']:>3}"
            )

        msg = "\n".join(lines)
        send_telegram_message(msg)


if __name__ == "__main__":
    main()
