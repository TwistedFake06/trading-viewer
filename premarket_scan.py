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
    """
    期權流動性 + 流量評分：
    - liq_score: ATM ±5% 成交量 0-3 分（原本邏輯）
    - flow_score: Volume / OI / Put-Call Ratio 0-4 分
    - total: liq_score + flow_score
    回傳 dict，方便後續擴充
    """
    try:
        tick = yf.Ticker(symbol)
        if not tick.options:
            return {
                "liq_score": 0,
                "flow_score": 0,
                "total": 0,
                "pc_ratio": 0.0,
                "atm_vol": 0,
                "atm_oi": 0,
            }

        # 最近一個到期日
        expiry = tick.options[0]
        chain = tick.option_chain(expiry)
        calls = chain.calls
        puts = chain.puts

        price = tick.fast_info.last_price
        if not price:
            return {
                "liq_score": 0,
                "flow_score": 0,
                "total": 0,
                "pc_ratio": 0.0,
                "atm_vol": 0,
                "atm_oi": 0,
            }

        # 只看 ATM ±5%
        lower = price * 0.95
        upper = price * 1.05
        atm_calls = calls[(calls["strike"] >= lower) & (calls["strike"] <= upper)]
        atm_puts = puts[(puts["strike"] >= lower) & (puts["strike"] <= upper)]

        if atm_calls.empty and atm_puts.empty:
            return {
                "liq_score": 0,
                "flow_score": 0,
                "total": 0,
                "pc_ratio": 0.0,
                "atm_vol": 0,
                "atm_oi": 0,
            }

        # --- 基礎流動性分數（沿用舊規則） ---
        vol_atm = atm_calls["volume"].sum() + atm_puts["volume"].sum()
        if vol_atm > 5000:
            liq_score = 3
        elif vol_atm > 1000:
            liq_score = 2
        elif vol_atm > 100:
            liq_score = 1
        else:
            liq_score = 0

        # --- 新增：Volume / OI / Put-Call Ratio ---
        call_vol = atm_calls["volume"].sum()
        put_vol = atm_puts["volume"].sum()
        call_oi = atm_calls["openInterest"].sum() if "openInterest" in atm_calls.columns else 0
        put_oi = atm_puts["openInterest"].sum() if "openInterest" in atm_puts.columns else 0

        vol_sum = vol_atm
        oi_sum = call_oi + put_oi

        # Put/Call Volume Ratio
        pc_ratio = float(put_vol) / float(call_vol if call_vol > 0 else 1)

        flow_score = 0

        # 1) Volume 等級
        if vol_sum > 10000:
            flow_score += 2
        elif vol_sum > 3000:
            flow_score += 1

        # 2) OI 等級
        if oi_sum > 20000:
            flow_score += 2
        elif oi_sum > 5000:
            flow_score += 1

        # 3) Put-Call Ratio 情緒（只加 1 分，偏向方向感）
        if pc_ratio > 1.2 or pc_ratio < 0.8:
            flow_score += 1

        total = liq_score + flow_score

        return {
            "liq_score": int(liq_score),
            "flow_score": int(flow_score),
            "total": int(total),
            "pc_ratio": float(pc_ratio),
            "atm_vol": int(vol_atm),
            "atm_oi": int(oi_sum),
        }

    except Exception:
        return {
            "liq_score": 0,
            "flow_score": 0,
            "total": 0,
            "pc_ratio": 0.0,
            "atm_vol": 0,
            "atm_oi": 0,
        }


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

            # 3. 期權流動性 + flow 分數
            opt = get_options_score(sym)
            opt_score = opt["total"]

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
                "opt_liq_score": int(opt["liq_score"]),
                "opt_flow_score": int(opt["flow_score"]),
                "opt_total_score": int(opt["total"]),
                "pc_ratio": float(opt["pc_ratio"]),
                "atm_vol": int(opt["atm_vol"]),
                "atm_oi": int(opt["atm_oi"]),
                "total_score": int(total_score),
                "scenario": scenario,
                "pre_source": pre.get("source", "unknown"),
            }

            results.append(row)
            print(
                f" - {sym}: prev_trend={row['prev_trend']}, "
                f"gap={row['gap_pct']:+.2f}%, opt_total={opt_score}, "
                f"score={total_score}, scenario={scenario}, "
                f"atm_vol={row['atm_vol']}, atm_oi={row['atm_oi']}, "
                f"pc={row['pc_ratio']:.2f}, src={row['pre_source']}"
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
                f"{r['opt_total_score']:>3}   {r['total_score']:>3}"
            )

        msg = "\n".join(lines)
        send_telegram_message(msg)


if __name__ == "__main__":
    main()
