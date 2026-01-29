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

    # 這裡先只拿第一列的 Volume 做實驗，確認類型
    vol_series = df["Volume"]
    print(f"[DEBUG] Volume dtype: {vol_series.dtype}, sample: {vol_series.head()}")

    vol_sum_raw = vol_series.sum()
    print(f"[DEBUG] vol_sum_raw type: {type(vol_sum_raw)}, value: {vol_sum_raw}")

    # 強制用 float() 試一次，如果這裡還爆，就可以精準看到是哪個 type
    vol_sum = float(vol_sum_raw)
    print(f"[DEBUG] vol_sum float: {vol_sum}")

    # 若能走到這裡，代表 float() 已經不會再抱怨 Series
    tp = (df["High"] + df["Low"]) / 2.0
    pv = tp * df["Volume"]
    vwap = float(pv.sum()) / vol_sum
    close = float(df["Close"].iloc[-1])
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
