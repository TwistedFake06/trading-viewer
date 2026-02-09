# utils.py
import os
import requests
import logging
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram_message(text: str, parse_mode: str = "Markdown"):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        logging.warning("Telegram env not set, skip sending.")
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            logging.warning(f"Telegram send failed: {resp.text}")
        else:
            logging.info("Telegram sent.")
    except Exception as e:
        logging.warning(f"Telegram exception: {e}")

def normalize_dataframe(df: pd.DataFrame, symbol: str = None):
    if isinstance(df.columns, pd.MultiIndex):
        if symbol:
            df.columns = [col[0] for col in df.columns.get_level_values(0)]  # 取 Price Type
        else:
            df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower().strip() for c in df.columns]
    if "close" not in df.columns and "adj close" in df.columns:
        df = df.rename(columns={"adj close": "close"})
    required = ["open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return None, f"Missing columns: {missing}"
    return df[required], None

def get_last_trading_day_vwap(symbol: str, interval: str = "5m", max_days: int = 7):
    date = datetime.now().date()
    for i in range(1, max_days + 1):
        target_date = date - timedelta(days=i)
        start_str = target_date.strftime("%Y-%m-%d")
        end_str = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
        try:
            df = yf.download(symbol, interval=interval, start=start_str, end=end_str, progress=False)
            if df.empty or len(df) < 10:
                continue
            df_norm, err = normalize_dataframe(df)
            if err:
                continue
            high, low, vol = df_norm["high"], df_norm["low"], df_norm["volume"]
            tp = (high + low) / 2.0
            pv = tp * vol
            vwap = pv.sum() / vol.sum()
            close = float(df_norm["close"].iloc[-1])
            pct = (close - vwap) / vwap * 100.0
            trend = "Bullish" if pct > 0.3 else "Bearish" if pct < -0.3 else "Neutral"
            return {"date": start_str, "prev_close": close, "prev_vwap": vwap, "prev_trend": trend}
        except Exception as e:
            logging.warning(f"VWAP error for {symbol} on {start_str}: {e}")
    return None

def calc_vwap_for_symbol(symbol: str, date_str: str, interval: str = "5m", max_retry_days: int = 7):
    for days_ago in range(max_retry_days + 1):
        actual_date = datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=days_ago)
        actual_date_str = actual_date.strftime("%Y-%m-%d")
        start_str = actual_date_str
        end_str = (actual_date + timedelta(days=1)).strftime("%Y-%m-%d")
        try:
            df = yf.download(symbol, interval=interval, start=start_str, end=end_str, prepost=True, progress=False)
            if df.empty or len(df) < 10:
                continue
            df_norm, err = normalize_dataframe(df)
            if err:
                continue
            save_intraday_data(df_norm, symbol, actual_date_str)
            high, low, vol = df_norm["high"], df_norm["low"], df_norm["volume"]
            vol_sum = float(vol.sum())
            if vol_sum == 0:
                continue
            tp = (high + low) / 2.0
            pv = tp * vol
            vwap = float(pv.sum()) / vol_sum
            close = float(df_norm["close"].iloc[-1])
            pct = (close - vwap) / vwap * 100.0
            return {"symbol": symbol, "date": actual_date_str, "close": round(close, 4), "vwap": round(vwap, 4), "close_vwap_pct": round(pct, 4)}
        except Exception as e:
            logging.warning(f"Calc VWAP error for {symbol} on {actual_date_str}: {e}")
    return None

def save_intraday_data(df: pd.DataFrame, symbol: str, date_str: str):
    try:
        temp_df = df.copy()
        temp_df["tp"] = (temp_df["high"] + temp_df["low"] + temp_df["close"]) / 3
        temp_df["pv"] = temp_df["tp"] * temp_df["volume"]
        temp_df["cum_pv"] = temp_df["pv"].cumsum()
        temp_df["cum_vol"] = temp_df["volume"].cumsum()
        temp_df["vwap"] = temp_df["cum_pv"] / temp_df["cum_vol"].replace(0, 1)
        chart_data = []
        for idx, row in temp_df.iterrows():
            ts = int(idx.timestamp())
            chart_data.append({
                "time": ts, "open": round(row["open"], 2), "high": round(row["high"], 2),
                "low": round(row["low"], 2), "close": round(row["close"], 2),
                "volume": int(row["volume"]), "vwap": round(row["vwap"], 2)
            })
        dir_path = "data/intraday"
        os.makedirs(dir_path, exist_ok=True)
        file_path = f"{dir_path}/intraday_{symbol}_{date_str}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(chart_data, f)
        logging.info(f"Saved chart data: {file_path} ({len(chart_data)} bars)")
    except Exception as e:
        logging.warning(f"Failed to save intraday for {symbol}: {e}")