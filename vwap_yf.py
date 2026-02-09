# vwap_yf.py
# 最終完整版：累加到單一 JSON、處理 MultiIndex、交易日檢查、回溯

import argparse
import json
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

# 如果有 utils.py 放 Telegram 函數，可 import
# from utils import send_telegram_message

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def is_trading_day(symbol: str, date_str: str) -> bool:
    """檢查指定日期是否為美股交易日（有 volume > 0 且有 Close）"""
    try:
        start = date_str
        end = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        df = yf.download(symbol, start=start, end=end, interval="1d", progress=False)

        if df.empty:
            logging.debug(f"{date_str} 無資料 (empty)")
            return False

        # 處理 MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.columns = [str(c).lower().strip() for c in df.columns]

        if "adj close" in df.columns and "close" not in df.columns:
            df["close"] = df["adj close"]

        if "volume" not in df.columns or "close" not in df.columns:
            return False

        last_row = df.iloc[-1]
        return float(last_row["volume"]) > 0 and pd.notna(last_row["close"])

    except Exception as e:
        logging.warning(f"檢查交易日失敗 {symbol} {date_str}: {e}")
        return False


def json_exists(symbol: str, date_str: str) -> bool:
    # 檢查單日 JSON 是否存在（舊邏輯，可保留或移除）
    path = f"data/intraday/intraday_{symbol}_{date_str}.json"
    if os.path.exists(path):
        logging.info(f"單日 JSON 已存在: {path}")
        return True
    return False


def append_or_merge_intraday_json(symbol: str, date_str: str, df: pd.DataFrame) -> str:
    """將新一天資料累加到統一的 intraday_{symbol}.json"""
    try:
        df = df.copy()

        # 處理欄位
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(c).lower().strip() for c in df.columns]

        if "adj close" in df.columns and "close" not in df.columns:
            df["close"] = df["adj close"]
            df = df.drop(columns=["adj close"], errors='ignore')

        required = ["open", "high", "low", "close", "volume"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise KeyError(f"缺少欄位: {missing}. 可用: {list(df.columns)}")

        # 計算 VWAP
        df["tp"] = (df["high"] + df["low"] + df["close"]) / 3
        df["pv"] = df["tp"] * df["volume"]
        df["cum_pv"] = df["pv"].cumsum()
        df["cum_vol"] = df["volume"].cumsum()
        df["vwap"] = df["cum_pv"] / df["cum_vol"].replace(0, 1)

        # 新資料轉 dict list
        new_data = []
        for idx, row in df.iterrows():
            ts = int(idx.timestamp())
            new_data.append({
                "time": ts,
                "open": round(float(row["open"]), 2),
                "high": round(float(row["high"]), 2),
                "low": round(float(row["low"]), 2),
                "close": round(float(row["close"]), 2),
                "volume": int(row["volume"]),
                "vwap": round(float(row["vwap"]), 2),
            })

        # 目標檔案：統一累加檔
        os.makedirs("data/intraday", exist_ok=True)
        path = f"data/intraday/intraday_{symbol}.json"

        # 讀舊資料
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            logging.info(f"讀取舊資料: {path} ({len(existing_data)} 筆)")
        else:
            existing_data = []
            logging.info(f"建立新累加檔: {path}")

        # 合併 + 去重（以 time 為 key）
        time_set = {d["time"] for d in existing_data}
        merged_data = existing_data[:]
        added_count = 0
        for d in new_data:
            if d["time"] not in time_set:
                merged_data.append(d)
                time_set.add(d["time"])
                added_count += 1

        # 按 time 排序
        merged_data.sort(key=lambda x: x["time"])

        # 寫回
        with open(path, "w", encoding="utf-8") as f:
            json.dump(merged_data, f, indent=2)
        logging.info(f"累加完成: {path} (新增 {added_count} 筆，總計 {len(merged_data)} 筆)")

        return path

    except KeyError as ke:
        logging.error(f"欄位錯誤 {symbol} {date_str}: {ke}")
        return ""
    except Exception as e:
        logging.error(f"合併/儲存失敗 {symbol} {date_str}: {e}")
        return ""


def process_symbol(symbol: str, target_date_input: str, interval: str = "5m", max_back_days: int = 7):
    if target_date_input.lower() == "yesterday":
        target_date = datetime.now() - timedelta(days=1)
    else:
        try:
            target_date = datetime.strptime(target_date_input, "%Y-%m-%d")
        except ValueError:
            logging.error(f"無效日期: {target_date_input}")
            return

    target_date_str = target_date.strftime("%Y-%m-%d")
    logging.info(f"處理 {symbol}，目標 {target_date_str} (回溯最多 {max_back_days} 天)")

    found = False
    for days_ago in range(0, max_back_days + 1):
        check_date = target_date - timedelta(days=days_ago)
        check_date_str = check_date.strftime("%Y-%m-%d")

        if not is_trading_day(symbol, check_date_str):
            logging.info(f"{check_date_str} 非交易日，跳過 ({symbol})")
            continue

        # 因為我們現在累加到統一檔案，不再檢查單日 JSON
        # 直接抓取並累加
        try:
            start = check_date_str
            end = (check_date + timedelta(days=1)).strftime("%Y-%m-%d")
            df = yf.download(symbol, interval=interval, start=start, end=end, prepost=True, progress=False)

            if df.empty or len(df) < 5:
                logging.warning(f"無 intraday 資料 {symbol} {check_date_str}")
                continue

            json_path = append_or_merge_intraday_json(symbol, check_date_str, df)
            if json_path:
                found = True
                logging.info(f"成功累加 {symbol} on {check_date_str}")
                break

        except Exception as e:
            logging.error(f"下載失敗 {symbol} {check_date_str}: {e}")
            continue

    if not found:
        logging.error(f"找不到任何交易日資料 {symbol} (回溯 {max_back_days} 天)")


def main():
    parser = argparse.ArgumentParser(description="VWAP Calculation - Append to single JSON per symbol")
    parser.add_argument("date", nargs="?", default="yesterday", help="Target date YYYY-MM-DD or 'yesterday'")
    parser.add_argument("symbols", help="Comma-separated symbols")
    parser.add_argument("--interval", default="5m", help="Interval e.g. 5m")
    parser.add_argument("--max-back", type=int, default=7, help="Max days to backtrack")
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    logging.info(f"開始處理 {len(symbols)} 個股票，目標 {args.date} (回溯最多 {args.max_back} 天)")

    for sym in symbols:
        process_symbol(sym, args.date, args.interval, args.max_back)

    msg = f"VWAP 更新完成\n目標日期: {args.date} (及回溯)\n符號: {', '.join(symbols)}"
    # send_telegram_message(msg)  # 如有就取消註解


if __name__ == "__main__":
    main()