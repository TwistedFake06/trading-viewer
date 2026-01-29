import sys
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf

# 使用方式：
#   python vwap_yf.py 2026-01-28 AMD,NVDA,TSLA
#
# 會在 data/vwap_2026-01-28.json 輸出:
# [
#   {"symbol":"AMD","date":"2026-01-28","close":..., "vwap":..., "close_vwap_pct":...},
#   ...
# ]

def calc_vwap_for_symbol(symbol: str, date_str: str):
  date = datetime.strptime(date_str, "%Y-%m-%d").date()
  next_date = date + timedelta(days=1)

  df = yf.download(
      symbol,
      interval="1m",
      start=date.strftime("%Y-%m-%d"),
      end=next_date.strftime("%Y-%m-%d"),
      progress=False
  )

  if df.empty:
    return None

  # typical price = (High + Low) / 2
  tp = (df["High"] + df["Low"]) / 2
  pv = tp * df["Volume"]

  vol_sum = df["Volume"].sum()
  if vol_sum == 0:
    return None

  vwap = (pv.sum() / vol_sum).item()
  close = df["Close"].iloc[-1].item()
  pct = (close - vwap) / vwap * 100

  result = {
      "symbol": symbol,
      "date": date_str,
      "close": round(close, 4),
      "vwap": round(vwap, 4),
      "close_vwap_pct": round(pct, 4)
  }
  return result


def main():
  if len(sys.argv) < 3:
    print("Usage: python vwap_yf.py YYYY-MM-DD AMD,NVDA,TSLA", file=sys.stderr)
    sys.exit(1)

  date_str = sys.argv[1]
  symbols_str = sys.argv[2]
  symbols = [s.strip().upper() for s in symbols_str.split(",") if s.strip()]

  results = []
  for sym in symbols:
    print(f"Processing {sym} {date_str} ...")
    res = calc_vwap_for_symbol(sym, date_str)
    if res is not None:
      results.append(res)

  if not results:
    print("No data for given date/symbols")
    return

  # 確保有 data 目錄
  import os
  os.makedirs("data", exist_ok=True)

  out_path = f"data/vwap_{date_str}.json"
  with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

  print(f"Wrote {out_path} with {len(results)} records")


if __name__ == "__main__":
  main()
