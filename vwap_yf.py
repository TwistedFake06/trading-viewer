# vwap_yf.py
# 支援 --max-back 參數的完整版本

import argparse
import json
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

from utils import send_telegram_message  # 如果你有這個函數

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def is_trading_day(symbol: str, date_str: str) -> bool:
    try:
        start = date_str
        end = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        df = yf.download(symbol, start=start, end=end, interval="1d", progress=False)
        if df.empty:
            return False
        df.columns = [c.lower() for c in df.columns]
        if "volume" not in df or "close" not in df:
            return False
        last_row = df.iloc[-1]
        return last_row["volume"] > 0 and pd.notna(last_row["close"])
    except Exception as e:
        logging.warning(f"檢查交易日失敗 {symbol} {date_str}: {e}")
        return False

def json_exists(symbol: str, date_str: str) -> bool:
    path = f"data/intraday/intraday_{symbol}_{date_str}.json"
    exists = os.path.exists(path)
    if exists:
        logging.info(f"JSON 已存在，跳過: {path}")
    return exists

def save_intraday_json(symbol: str, date_str: str, df: pd.DataFrame) -> str:
    try:
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        if "adj close" in df and "close" not in df:
            df["close"] = df["adj close"]

        df["tp"] = (df["high"] + df["low"] + df["close"]) / 3
        df["pv"] = df["tp"] * df["volume"]
        df["cum_pv"] = df["pv"].cumsum()
        df["cum_vol"] = df["volume"].cumsum()
        df["vwap"] = df["cum_pv"] / df["cum_vol"].replace(0, 1)

        chart_data = []
        for idx, row in df.iterrows():
            ts = int(idx.timestamp())
            chart_data.append({
                "time": ts,
                "open": round(float(row["open"]), 2),
                "high": round(float(row["high"]), 2),
                "low": round(float(row["low"]), 2),
                "close": round(float(row["close"]), 2),
                "volume": int(row["volume"]),
                "vwap": round(float(row["vwap"]), 2),
            })

        os.makedirs("data/intraday", exist_ok=True)
        path = f"data/intraday/intraday_{symbol}_{date_str}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(chart_data, f, indent=2)
        logging.info(f"儲存 JSON: {path} ({len(chart_data)} 筆)")
        return path
    except Exception as e:
        logging.error(f"儲存失敗 {symbol} {date_str}: {e}")
        return ""

def process_symbol(symbol: str, target_date_str: str, interval: str = "5m", max_back_days: int = 7):
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d") if target_date_str != "yesterday" else datetime.now() - timedelta(days=1)
    target_date_str = target_date.strftime("%Y-%m-%d")
    found = False

    for days_ago in range(0, max_back_days + 1):
        check_date = target_date - timedelta(days=days_ago)
        check_date_str = check_date.strftime("%Y-%m-%d")

        if not is_trading_day(symbol, check_date_str):
            logging.info(f"{check_date_str} 非交易日，跳過 ({symbol})")
            continue

        if json_exists(symbol, check_date_str):
            found = True
            break

        try:
            start = check_date_str
            end = (check_date + timedelta(days=1)).strftime("%Y-%m-%d")
            df = yf.download(symbol, interval=interval, start=start, end=end, prepost=True, progress=False)

            if df.empty or len(df) < 5:
                logging.warning(f"無 intraday 資料 {symbol} {check_date_str}")
                continue

            json_path = save_intraday_json(symbol, check_date_str, df)
            if json_path:
                found = True
                logging.info(f"成功處理 {symbol} on {check_date_str}")
                break
        except Exception as e:
            logging.error(f"下載失敗 {symbol} {check_date_str}: {e}")
            continue

    if not found:
        logging.error(f"找不到交易日資料 {symbol} (回溯 {max_back_days} 天)")

def main():
    parser = argparse.ArgumentParser(description="VWAP Calculation - Trading Day Check & Skip Existing JSON")
    parser.add_argument("date", nargs="?", default="yesterday", help="Target date YYYY-MM-DD or 'yesterday'")
    parser.add_argument("symbols", help="Comma-separated symbols")
    parser.add_argument("--interval", default="5m", help="Interval e.g. 5m")
    parser.add_argument("--max-back", type=int, default=7, help="Max days to backtrack")
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    logging.info(f"開始處理 {len(symbols)} 個股票，目標 {args.date}")

    for sym in symbols:
        process_symbol(sym, args.date, args.interval, args.max_back)

    # 可選 Telegram 通知
    msg = f"VWAP 更新完成\n日期: {args.date} (及回溯)\n符號: {', '.join(symbols)}"
    send_telegram_message(msg)

if __name__ == "__main__":
    main()