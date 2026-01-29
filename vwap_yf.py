import sys
import json
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf


def calc_vwap_for_symbol(symbol: str, date_str: str):
    date = datetime.strptime(date_str, "%Y-%m-%d").date()
    next_date = date + timedelta(days=1)

    print(f"[DEBUG] Downloading {symbol} {date_str} 1m data ...")
    df = yf.download(
        symbol,
        interval="1m",
        start=date.strftime("%Y-%m-%d"),
        end=next_date.strftime("%Y-%m-%d"),
        progress=False
    )

    print(f"[DEBUG] df type: {type(df)}")
    print(f"[DEBUG] df.head():\n{df.head()}")
    print(f"[DEBUG] df.columns: {list(df.columns)}")

    if df.empty:
        print(f"[WARN] {symbol} {date_str} 無資料（df.empty）")
        return None

    # 處理 MultiIndex 欄位：('Close','AMD') 這一類
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

    # 確保必要欄位存在
    for col in [close_col, high_col, low_col, vol_col]:
        if col not in df.columns:
            print(f"[WARN] {symbol} {date_str} 缺少欄位 {col}，跳過。")
            return None

    high = df[high_col]
    low = df[low_col]
    vol = df[vol_col]

    print(f"[DEBUG] Volume sample:\n{vol.head()}")
    print(f"[DEBUG] Volume dtype: {vol.dtype}")

    tp = (high + low) / 2.0
    pv = tp * vol

    vol_sum_raw = vol.sum()
    print(f"[DEBUG] vol_sum_raw type: {type(vol_sum_raw)}, value: {vol_sum_raw}")

    vol_sum = float(vol_sum_raw)
    if vol_sum == 0.0:
        print(f"[WARN] {symbol} {date_str} 成交量總和為 0，跳過。")
        return None

    vwap = float(pv.sum()) / vol_sum
    close = float(df[close_col].iloc[-1])
    pct = (close - vwap) / vwap * 100.0

    return {
        "symbol": symbol,
        "date": date_str,
        "close": round(close, 4),
        "vwap": round(vwap, 4),
        "close_vwap_pct": round(pct, 4)
    }


def main():
    # 暫時只支援一個 symbol，簡化 debug
    if len(sys.argv) < 3:
        print("Usage: python vwap_yf.py YYYY-MM-DD AMD", file=sys.stderr)
        sys.exit(1)

    date_str = sys.argv[1]
    symbol = sys.argv[2].strip().upper()

    print(f"[INFO] Start VWAP calc for {symbol} {date_str}")
    res = calc_vwap_for_symbol(symbol, date_str)

    if res is None:
        print("[WARN] 沒有任何結果。")
        return

    import os
    os.makedirs("data", exist_ok=True)
    out_path = f"data/vwap_{symbol}_{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Wrote {out_path}")


if __name__ == "__main__":
    main()
