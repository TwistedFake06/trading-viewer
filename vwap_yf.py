# vwap_yf.py
# 最終完整版：處理 MultiIndex、正確判斷交易日、回溯、跳過已存在 JSON

import argparse
import json
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

# 如果你有 utils.py 放 Telegram 函數，就 import；否則可註解
# from utils import send_telegram_message

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def is_trading_day(symbol: str, date_str: str) -> bool:
    """檢查指定日期是否為美股交易日（有 volume > 0 且有 Close）"""
    try:
        start = date_str
        end = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        df = yf.download(symbol, start=start, end=end, interval="1d", progress=False)

        if df.empty:
            logging.debug(f"{date_str} 無資料 (empty DataFrame)")
            return False

        # 處理 MultiIndex 欄位（yfinance 常見）
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 轉小寫 + 去除空白
        df.columns = [str(c).lower().strip() for c in df.columns]

        # 處理 adj close → close
        if "adj close" in df.columns and "close" not in df.columns:
            df["close"] = df["adj close"]
            df = df.drop(columns=["adj close"], errors='ignore')

        # 檢查必要欄位
        required = ["volume", "close"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            logging.debug(f"{date_str} 缺少欄位: {missing}")
            return False

        last_row = df.iloc[-1]
        volume_ok = float(last_row["volume"]) > 0
        close_ok = pd.notna(last_row["close"])

        logging.debug(f"{date_str} 檢查: volume={last_row.get('volume', 'N/A')}, close={last_row.get('close', 'N/A')}, is_trading={volume_ok and close_ok}")

        return volume_ok and close_ok

    except Exception as e:
        logging.warning(f"檢查交易日失敗 {symbol} {date_str}: {str(e)}")
        return False


def json_exists(symbol: str, date_str: str) -> bool:
    path = f"data/intraday/intraday_{symbol}_{date_str}.json"
    if os.path.exists(path):
        logging.info(f"JSON 已存在，跳過重抓: {path}")
        return True
    return False


def save_intraday_json(symbol: str, date_str: str, df: pd.DataFrame) -> str:
    try:
        df = df.copy()

        # 強制處理 MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.columns = [str(c).lower().strip() for c in df.columns]

        if "adj close" in df.columns and "close" not in df.columns:
            df["close"] = df["adj close"]
            df = df.drop(columns=["adj close"], errors='ignore')

        # 檢查必要欄位
        required = ["open", "high", "low", "close", "volume"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise KeyError(f"缺少必要欄位: {missing}。可用欄位: {list(df.columns)}")

        # 計算 VWAP
        df["tp"] = (df["high"] + df["low"] + df["close"]) / 3
        df["pv"] = df["tp"] * df["volume"]
        df["cum_pv"] = df["pv"].cumsum()
        df["cum_vol"] = df["volume"].cumsum()
        df["vwap"] = df["cum_pv"] / df["cum_vol"].replace(0, 1)

        # 產生 chart_data
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
        logging.info(f"已儲存: {path} ({len(chart_data)} 筆資料)")
        return path

    except KeyError as ke:
        logging.error(f"欄位錯誤 {symbol} {date_str}: {ke}")
        return ""
    except Exception as e:
        logging.error(f"儲存 JSON 失敗 {symbol} {date_str}: {str(e)}")
        return ""


def process_symbol(symbol: str, target_date_input: str, interval: str = "5m", max_back_days: int = 7):
    # 處理日期輸入（支援 "yesterday"）
    if target_date_input.lower() == "yesterday":
        target_date = datetime.now() - timedelta(days=1)
    else:
        try:
            target_date = datetime.strptime(target_date_input, "%Y-%m-%d")
        except ValueError:
            logging.error(f"無效日期格式: {target_date_input}")
            return

    target_date_str = target_date.strftime("%Y-%m-%d")
    logging.info(f"處理 {symbol}，目標日期 {target_date_str} (回溯最多 {max_back_days} 天)")

    found = False
    for days_ago in range(0, max_back_days + 1):
        check_date = target_date - timedelta(days=days_ago)
        check_date_str = check_date.strftime("%Y-%m-%d")

        # 1. 檢查是否交易日
        if not is_trading_day(symbol, check_date_str):
            logging.info(f"{check_date_str} 非交易日，跳過 ({symbol})")
            continue

        # 2. 檢查 JSON 是否已存在
        if json_exists(symbol, check_date_str):
            found = True
            break

        # 3. 抓取並儲存
        try:
            start = check_date_str
            end = (check_date + timedelta(days=1)).strftime("%Y-%m-%d")
            df = yf.download(
                symbol,
                interval=interval,
                start=start,
                end=end,
                prepost=True,
                progress=False
            )

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
        logging.error(f"找不到任何交易日資料 {symbol} (回溯 {max_back_days} 天)")


def main():
    parser = argparse.ArgumentParser(description="VWAP Calculation - Auto check trading day & skip existing JSON")
    parser.add_argument("date", nargs="?", default="yesterday", help="Target date YYYY-MM-DD or 'yesterday'")
    parser.add_argument("symbols", help="Comma-separated symbols")
    parser.add_argument("--interval", default="5m", help="Interval e.g. 5m")
    parser.add_argument("--max-back", type=int, default=7, help="Max days to backtrack for trading day")
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    logging.info(f"開始處理 {len(symbols)} 個股票，目標 {args.date} (回溯最多 {args.max_back} 天)")

    for sym in symbols:
        process_symbol(sym, args.date, args.interval, args.max_back)

    # 可選：發送 Telegram 通知
    msg = f"VWAP 更新完成\n目標日期: {args.date} (及回溯)\n符號: {', '.join(symbols)}"
    # send_telegram_message(msg)  # 如有就取消註解


if __name__ == "__main__":
    main()