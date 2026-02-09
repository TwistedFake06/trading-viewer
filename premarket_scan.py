# premarket_scan.py
import argparse
import json
import os
from datetime import datetime
import pandas as pd
import yfinance as yf
from utils import get_last_trading_day_vwap, send_telegram_message, logging

def get_premarket_data(symbol: str):
    try:
        tick = yf.Ticker(symbol)
        pre_price = tick.info.get("preMarketPrice")
        fast = tick.fast_info
        last_price = fast.last_price
        prev_close = fast.previous_close
        if not prev_close:
            return None
        price = float(pre_price) if pre_price and pre_price > 0 else float(last_price) if last_price else None
        source = "preMarketPrice" if pre_price else "last_price"
        if price is None:
            return None
        gap_pct = (price - prev_close) / prev_close * 100.0
        return {"price": price, "prev_close": float(prev_close), "gap_pct": gap_pct, "source": source}
    except Exception as e:
        logging.warning(f"Premarket data error for {symbol}: {e}")
        return None

def get_options_score(symbol: str):
    try:
        tick = yf.Ticker(symbol)
        expiry = tick.options[0] if tick.options else None
        if not expiry:
            return {"liq_score": 0, "flow_score": 0, "total": 0, "pc_ratio": 0.0, "atm_vol": 0, "atm_oi": 0}
        chain = tick.option_chain(expiry)
        calls, puts = chain.calls, chain.puts
        price = tick.fast_info.last_price
        atm_calls = calls[(calls["strike"] >= price * 0.95) & (calls["strike"] <= price * 1.05)]
        atm_puts = puts[(puts["strike"] >= price * 0.95) & (puts["strike"] <= price * 1.05)]
        atm_vol = int(atm_calls["volume"].sum() + atm_puts["volume"].sum())
        atm_oi = int(atm_calls["openInterest"].sum() + atm_puts["openInterest"].sum())
        pc_ratio = atm_puts["volume"].sum() / atm_calls["volume"].sum() if atm_calls["volume"].sum() > 0 else 0.0
        liq_score = 3 if atm_vol > 10000 else 2 if atm_vol > 5000 else 1 if atm_vol > 1000 else 0
        flow_score = 1 if atm_oi > 5000 else 0
        if pc_ratio > 1.5 or pc_ratio < 0.5:
            flow_score += 1
        total = liq_score + flow_score
        return {"liq_score": liq_score, "flow_score": flow_score, "total": total, "pc_ratio": pc_ratio, "atm_vol": atm_vol, "atm_oi": atm_oi}
    except Exception as e:
        logging.warning(f"Options score error for {symbol}: {e}")
        return {"liq_score": 0, "flow_score": 0, "total": 0, "pc_ratio": 0.0, "atm_vol": 0, "atm_oi": 0}

def decide_scenario(total_score: int):
    return "A" if total_score >= 6 else "C" if total_score <= 2 else "B"

def main():
    parser = argparse.ArgumentParser(description="Premarket Scan")
    parser.add_argument("symbols", type=str, help="Comma-separated symbols e.g. AMD,NVDA")
    args = parser.parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    results = []
    for sym in symbols:
        try:
            prev = get_last_trading_day_vwap(sym) or {"prev_trend": "N/A", "prev_close": 0.0}
            pre = get_premarket_data(sym) or {"price": prev["prev_close"], "prev_close": prev["prev_close"], "gap_pct": 0.0, "source": "fallback"}
            opt = get_options_score(sym)
            opt_score = opt["total"]
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
                "symbol": sym, "prev_trend": prev["prev_trend"], "prev_close": float(pre["prev_close"]),
                "price": float(pre["price"]), "gap_pct": float(pre["gap_pct"]),
                "opt_liq_score": int(opt["liq_score"]), "opt_flow_score": int(opt["flow_score"]),
                "opt_total_score": int(opt["total"]), "pc_ratio": float(opt["pc_ratio"]),
                "atm_vol": int(opt["atm_vol"]), "atm_oi": int(opt["atm_oi"]),
                "total_score": int(total_score), "scenario": scenario, "pre_source": pre.get("source", "unknown")
            }
            results.append(row)
            logging.info(f"{sym}: trend={row['prev_trend']}, gap={row['gap_pct']:+.2f}%, opt={opt_score}, score={total_score}, scenario={scenario}")
        except Exception as e:
            logging.error(f"Error {sym}: {e}")
    if results:
        today = datetime.now().strftime("%Y-%m-%d")
        os.makedirs("data", exist_ok=True)
        out_path = f"data/premarket_{today}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logging.info(f"Saved to {out_path}")
        sorted_res = sorted(results, key=lambda x: x["total_score"], reverse=True)
        lines = [f"*Premarket Scan {today}*", "`Ticker  Scen  Prev  Px   Δ%    Opt  Score`"]
        for r in sorted_res:
            lines.append(f"{r['symbol']:>5}  {r['scenario']:<4}  {r['prev_trend'][:4]:>4}  {r['price']:>6.2f}  {r['gap_pct']:+5.2f}%  {r['opt_total_score']:>3}   {r['total_score']:>3}")
        send_telegram_message("\n".join(lines))

if __name__ == "__main__":
    main()