import sys
import json
import os
import traceback
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from telegram_utils import send_telegram_message


def normalize_dataframe(df: pd.DataFrame):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower().strip() for c in df.columns]

    if "close" not in df.columns and "adj close" in df.columns:
        df = df.rename(columns={"adj close": "close"})

    required = ["open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return None, f"Missing columns after normalization: {missing}. Available: {list(df.columns)}"

    return df[required], None


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
            chart_data.append(
                {
                    "time": ts,
                    "open": round(row["open"], 2),
                    "high": round(row["high"], 2),
                    "low": round(row["low"], 2),
                    "close": round(row["close"], 2),
                    "volume": int(row["volume"]),
                    "vwap": round(row["vwap"], 2),
                }
            )

        dir_path = "data/intraday"
        os.makedirs(dir_path, exist_ok=True)
        file_path = f"{dir_path}/intraday_{symbol}_{date_str}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(chart_data, f)

        print(f"[INFO] Saved chart data: {file_path} ({len(chart_data)} bars)")
    except Exception as e:
        print(f"[WARN] Failed to save intraday data for {symbol}: {e}")
        traceback.print_exc()


def calc_vwap_for_symbol(symbol: str, date_str: str, interval: str = "5m", max_retry_days: int = 7):
    date = datetime.strptime(date_str, "%Y-%m-%d").date()

    for days_ago in range(max_retry_days + 1):
        current_date = date - timedelta(days=days_ago)
        next_date = current_date + timedelta(days=1)
        actual_date_str = current_date.strftime("%Y-%m-%d")

        if days_ago > 0:
            print(f"[INFO] {symbol} {date_str} 無資料，嘗試 {actual_date_str} (往前 {days_ago} 天)")

        try:
            df = yf.download(
                symbol,
                interval=interval,
                start=actual_date_str,
                end=next_date.strftime("%Y-%m-%d"),
                progress=False,
                auto_adjust=False,
                group_by="column",
            )
        except Exception as e:
            print(f"[WARN] Download failed for {symbol}: {e}")
            continue

        if df.empty:
            if days_ago < max_retry_days:
                continue
            else:
                print(f"[WARN] {symbol} 往前找 {max_retry_days} 天都無資料，跳過。")
                return None

        df_norm, err = normalize_dataframe(df)
        if err:
            print(f"[WARN] {symbol} data error: {err}")
            if days_ago < max_retry_days:
                continue
            return None

        save_intraday_data(df_norm, symbol, actual_date_str)

        high = df_norm["high"]
        low = df_norm["low"]
        vol = df_norm["volume"]
        close_series = df_norm["close"]

        vol_sum = float(vol.sum())
        if vol_sum == 0:
            if days_ago < max_retry_days:
                continue
            return None

        tp = (high + low) / 2.0
        pv = tp * vol
        vwap = float(pv.sum()) / vol_sum
        close = float(close_series.iloc[-1])
        pct = (close - vwap) / vwap * 100.0

        return {
            "symbol": symbol,
            "date": actual_date_str,
            "close": round(close, 4),
            "vwap": round(vwap, 4),
            "close_vwap_pct": round(pct, 4),
        }

    return None


def main():
    if len(sys.argv) < 3:
        print("Usage: python vwap_yf.py YYYY-MM-DD SYMBOLS [interval]")
        sys.exit(1)

    date_str = sys.argv[1]
    symbols = [s.strip().upper() for s in sys.argv[2].split(",") if s.strip()]
    interval = sys.argv[3] if len(sys.argv) > 3 else "5m"

    results = []
    print(f"[INFO] Processing {len(symbols)} symbols for {date_str}...")

    for sym in symbols:
        try:
            res = calc_vwap_for_symbol(sym, date_str, interval=interval)
            if res:
                results.append(res)
        except Exception as e:
            print(f"[ERROR] {sym}: {e}")
            traceback.print_exc()

    if not results:
        print("[WARN] No results generated.")
        return

    os.makedirs("data", exist_ok=True)
    out_path = f"data/vwap_{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Summary saved to {out_path}")

    # Telegram 摘要（Top 5 by |close_vwap_pct|）
    try:
        sorted_res = sorted(results, key=lambda x: abs(x["close_vwap_pct"]), reverse=True)
        top = sorted_res[:5]

        lines = [f"*VWAP Summary {date_str}*"]
        lines.append("`Ticker  Close    VWAP    Δ%`")
        for r in top:
            lines.append(
                f"{r['symbol']:>5}  "
                f"{r['close']:>7.2f}  "
                f"{r['vwap']:>7.2f}  "
                f"{r['close_vwap_pct']:+5.2f}%"
            )

        msg = "\n".join(lines)
        send_telegram_message(msg)
    except Exception as e:
        print(f"[WARN] Failed to send Telegram summary: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
