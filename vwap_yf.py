import sys
import json
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf


def calc_vwap_for_symbol(symbol: str, date_str: str):
    """
    使用 yfinance 取得某一檔股票在指定日期的 1 分鐘資料，
    計算當日 VWAP、收盤價與收盤相對 VWAP 的百分比。
    """
    # 轉成日期物件
    date = datetime.strptime(date_str, "%Y-%m-%d").date()
    next_date = date + timedelta(days=1)

    # 抓取 [date, next_date) 區間的 1 分鐘 K 線
    df = yf.download(
        symbol,
        interval="1m",
        start=date.strftime("%Y-%m-%d"),
        end=next_date.strftime("%Y-%m-%d"),
        progress=False
    )

    if df.empty:
        print(f"[WARN] {symbol} {date_str} 無資料（df.empty）")
        return None

    # typical price = (High + Low) / 2
    tp = (df["High"] + df["Low"]) / 2.0
    pv = tp * df["Volume"]

    # 強制轉成純量，避免 pandas Series 的 truth value 問題
    vol_sum = float(df["Volume"].sum())
    if vol_sum == 0.0:
        print(f"[WARN] {symbol} {date_str} 成交量總和為 0，跳過。")
        return None

    vwap = float(pv.sum()) / vol_sum
    close = float(df["Close"].iloc[-1])
    pct = (close - vwap) / vwap * 100.0

    result = {
        "symbol": symbol,
        "date": date_str,
        "close": round(close, 4),
        "vwap": round(vwap, 4),
        "close_vwap_pct": round(pct, 4)
    }
    return result


def main():
    """
    用法：
        python vwap_yf.py YYYY-MM-DD AMD,NVDA,TSLA

    會在 data/vwap_YYYY-MM-DD.json 輸出：
    [
      {"symbol": "...", "date": "...", "close": ..., "vwap": ..., "close_vwap_pct": ...},
      ...
    ]
    """
    if len(sys.argv) < 3:
        print("Usage: python vwap_yf.py YYYY-MM-DD AMD,NVDA,TSLA", file=sys.stderr)
        sys.exit(1)

    date_str = sys.argv[1]
    symbols_str = sys.argv[2]
    symbols = [s.strip().upper() for s in symbols_str.split(",") if s.strip()]

    results = []
    for sym in symbols:
        print(f"Processing {sym} {date_str} ...")
        try:
            res = calc_vwap_for_symbol(sym, date_str)
        except Exception as e:
            print(f"[ERROR] {sym} {date_str} 計算失敗：{e}", file=sys.stderr)
            continue

        if res is not None:
            results.append(res)

    if not results:
        print("[WARN] 此日期／標的組合沒有任何可用結果。")
        return

    # 確保 data 目錄存在
    import os
    os.makedirs("data", exist_ok=True)

    out_path = f"data/vwap_{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"[INFO] Wrote {out_path} with {len(results)} records")


if __name__ == "__main__":
    main()
