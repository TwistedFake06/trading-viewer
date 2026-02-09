# vwap_yf.py
import argparse
import json
import os
from datetime import datetime
from utils import calc_vwap_for_symbol, send_telegram_message, logging

def main():
    parser = argparse.ArgumentParser(description="VWAP Calculation")
    parser.add_argument("date", type=str, help="Date YYYY-MM-DD")
    parser.add_argument("symbols", type=str, help="Comma-separated symbols")
    parser.add_argument("--interval", type=str, default="5m", help="Interval e.g. 5m")
    args = parser.parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    date_str = args.date
    results = []
    for sym in symbols:
        res = calc_vwap_for_symbol(sym, date_str, args.interval)
        if res:
            results.append(res)
    if results:
        os.makedirs("data", exist_ok=True)
        out_path = f"data/vwap_{date_str}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logging.info(f"Saved to {out_path}")
        sorted_res = sorted(results, key=lambda x: abs(x["close_vwap_pct"]), reverse=True)
        lines = [f"*VWAP Summary {date_str}*", "`Ticker  Close    VWAP    Δ%`"]
        for r in sorted_res[:5]:
            lines.append(f"{r['symbol']:>5}  {r['close']:>7.2f}  {r['vwap']:>7.2f}  {r['close_vwap_pct']:+5.2f}%")
        send_telegram_message("\n".join(lines))

if __name__ == "__main__":
    main()