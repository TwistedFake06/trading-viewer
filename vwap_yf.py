# vwap_yf.py
# 更新版：自動檢查前一天是否交易日，若無則回溯找最近交易日
# 若 JSON 已存在則跳過重抓

import argparse
import json
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def is_trading_day(symbol: str, date_str: str) -> bool:
    """檢查指定日期是否為美股交易日（有 volume > 0）"""
    try:
        df = yf.download(symbol, start=date_str, end=(datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"), interval="1d", progress=False)
        if df.empty:
            return False
        df_norm = df.copy()
        df_norm.columns = [c.lower() for c in df_norm.columns]
        if "volume" not in df_norm or df_norm["volume"].iloc[-1] == 0:
            return False
        return True
    except Exception as e:
        logging.warning(f"Check trading day error for {symbol} on {date_str}: {e}")
        return False

def find_latest_trading_day_data(symbol: str, target_date_str: str, max_back_days: int = 7, interval: str = "5m"):
    """從 target_date 開始回溯，找最近有資料的交易日，並檢查 JSON 是否存在"""
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    for days_ago in range(0, max_back_days + 1):
        check_date = target_date - timedelta(days=days_ago)
        check_date_str = check_date.strftime("%Y-%m-%d")

        # 先檢查是否交易日
        if not is_trading_day(symbol, check_date_str):
            logging.info(f"{check_date_str} 非交易日，跳過")
            continue

        # 檢查 JSON 是否已存在
        json_path = f"data/intraday/intraday_{symbol}_{check_date_str}.json"
        if os.path.exists(json_path):
            logging.info(f"JSON 已存在: {json_path}，跳過重抓")
            return check_date_str, json_path  # 回傳日期和路徑（可選用）

        # 抓 intraday 資料
        try:
            df = yf.download(symbol, interval=interval, start=check_date_str, end=(check_date + timedelta(days=1)).strftime("%Y-%m-%d"), prepost=True, progress=False)
            if df.empty or len(df) < 10:
                logging.warning(f"No intraday data for {symbol} on {check_date_str}")
                continue

            # 正規化欄位
            df.columns = [c.lower() for c in df.columns]
            if "adj close" in df and "close" not in df:
                df["close"] = df["adj close"]

            # 計算 VWAP
            df["tp"] = (df["high"] + df["low"] + df["close"]) / 3
            df["pv"] = df["tp"] * df["volume"]
            df["cum_pv"] = df["pv"].cumsum()
            df["cum_vol"] = df["volume"].cumsum()
            df["vwap"] = df["cum_pv"] / df["cum_vol"].replace(0, 1)

            # 存 JSON
            chart_data = []
            for idx, row in df.iterrows():
                ts = int(idx.timestamp())
                chart_data.append({
                    "time": ts,
                    "open": round(row["open"], 2),
                    "high": round(row["high"], 2),
                    "low": round(row["low"], 2),
                    "close": round(row["close"], 2),
                    "volume": int(row["volume"]),
                    "vwap": round(row["vwap"], 2),
                })

            os.makedirs("data/intraday", exist_ok=True)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(chart_data, f, indent=2)
            logging.info(f"Saved intraday data: {json_path} ({len(chart_data)} bars)")

            return check_date_str, json_path

        except Exception as e:
            logging.error(f"Download error for {symbol} on {check_date_str}: {e}")
            continue

    logging.error(f"No trading day data found for {symbol} in last {max_back_days} days")
    return None, None

def main():
    parser = argparse.ArgumentParser(description="VWAP Calculation with Trading Day Check")
    parser.add_argument("date", type=str, help="Target date YYYY-MM-DD (default: yesterday)")
    parser.add_argument("symbols", type=str, help="Comma-separated symbols")
    parser.add_argument("--interval", type=str, default="5m", help="Interval e.g. 5m")
    args = parser.parse_args()

    # 如果沒指定 date，用前一天
    if args.date == "yesterday" or not args.date:
        target_date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        target_date_str = args.date

    symbols = [s.strip().upper() for s in args.symbols.split(",")]

    for sym in symbols:
        logging.info(f"Processing {sym} for target {target_date_str}")
        actual_date, json_path = find_latest_trading_day_data(sym, target_date_str, interval=args.interval)
        if actual_date:
            logging.info(f"Processed {sym} on {actual_date}")

    # 可選：Telegram 通知（如果你有）
    # send_telegram_message("VWAP 更新完成")

if __name__ == "__main__":
    main()