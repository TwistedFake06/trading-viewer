import sys
import json
import os
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------
# Helper: Save Intraday Data for Charting
# ---------------------------------------------------------
def save_intraday_data(df, symbol, date_str):
    """
    將 DataFrame 轉成前端 Lightweight Charts 需要的格式並存檔
    格式: [{time, open, high, low, close, volume, vwap}, ...]
    """
    try:
        # 統一欄位名稱
        if isinstance(df.columns, pd.MultiIndex):
            col_map = {
                ("Open", symbol): "open", ("High", symbol): "high", 
                ("Low", symbol): "low", ("Close", symbol): "close", 
                ("Volume", symbol): "volume"
            }
        else:
            col_map = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
        
        # 複製並重命名
        temp_df = df.rename(columns=col_map).copy()
        
        # 確保只有這幾欄
        temp_df = temp_df[["open", "high", "low", "close", "volume"]]
        
        # 計算 Intraday VWAP Curve
        temp_df['tp'] = (temp_df['high'] + temp_df['low'] + temp_df['close']) / 3
        temp_df['pv'] = temp_df['tp'] * temp_df['volume']
        temp_df['cum_pv'] = temp_df['pv'].cumsum()
        temp_df['cum_vol'] = temp_df['volume'].cumsum()
        temp_df['vwap'] = temp_df['cum_pv'] / temp_df['cum_vol']
        
        # 轉 List of Dict
        chart_data = []
        for idx, row in temp_df.iterrows():
            # Time 轉 Unix Timestamp
            ts = int(idx.timestamp())
            chart_data.append({
                "time": ts,
                "open": round(row['open'], 2),
                "high": round(row['high'], 2),
                "low": round(row['low'], 2),
                "close": round(row['close'], 2),
                "volume": int(row['volume']),
                "vwap": round(row['vwap'], 2)
            })
            
        # 存檔
        dir_path = "data/intraday"
        os.makedirs(dir_path, exist_ok=True)
        file_path = f"{dir_path}/intraday_{symbol}_{date_str}.json"
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(chart_data, f)
            
        print(f"[INFO] Saved chart data: {file_path}")
        
    except Exception as e:
        print(f"[WARN] Failed to save intraday data for {symbol}: {e}")

# ---------------------------------------------------------
# Core Logic
# ---------------------------------------------------------
def calc_vwap_for_symbol(symbol: str, date_str: str, interval: str = "1m", max_retry_days: int = 7):
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
                progress=False
            )
        except Exception as e:
            print(f"[WARN] Download failed: {e}")
            continue
        
        if df.empty:
            if days_ago < max_retry_days: continue
            else:
                print(f"[WARN] {symbol} 往前找 {max_retry_days} 天都無資料，跳過。")
                return None
        
        # 欄位處理
        if isinstance(df.columns, pd.MultiIndex):
            close_col, high_col, low_col, vol_col = ("Close", symbol), ("High", symbol), ("Low", symbol), ("Volume", symbol)
        else:
            close_col, high_col, low_col, vol_col = "Close", "High", "Low", "Volume"
        
        missing = [c for c in [close_col, high_col, low_col, vol_col] if c not in df.columns]
        if missing:
            print(f"[WARN] {symbol} 缺少欄位 {missing}")
            if days_ago < max_retry_days: continue
            return None
        
        # --- 成功抓到資料後，先存一份給 Chart 用 ---
        save_intraday_data(df, symbol, actual_date_str)
        
        # 開始算 Summary VWAP
        high, low, vol = df[high_col], df[low_col], df[vol_col]
        
        vol_sum = float(vol.sum())
        if vol_sum == 0.0:
            print(f"[WARN] {symbol} Vol=0")
            if days_ago < max_retry_days: continue
            return None
            
        tp = (high + low) / 2.0
        pv = tp * vol
        vwap = float(pv.sum()) / vol_sum
        close = float(df[close_col].iloc[-1])
        pct = (close - vwap) / vwap * 100.0
        
        return {
            "symbol": symbol,
            "date": actual_date_str,
            "close": round(close, 4),
            "vwap": round(vwap, 4),
            "close_vwap_pct": round(pct, 4)
        }
    
    return None

def main():
    if len(sys.argv) < 3:
        print("Usage: python vwap_yf.py YYYY-MM-DD SYMBOLS [interval]")
        sys.exit(1)
    
    date_str = sys.argv[1]
    symbols = [s.strip().upper() for s in sys.argv[2].split(",") if s.strip()]
    interval = sys.argv[3] if len(sys.argv) > 3 else "1m"
    
    results = []
    print(f"[INFO] Processing {len(symbols)} symbols for {date_str}...")
    
    for sym in symbols:
        try:
            res = calc_vwap_for_symbol(sym, date_str, interval=interval)
            if res: results.append(res)
        except Exception as e:
            print(f"[ERROR] {sym}: {e}")
            
    if not results:
        print("[WARN] No results generated.")
        return
    
    os.makedirs("data", exist_ok=True)
    out_path = f"data/vwap_{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Summary saved to {out_path}")

if __name__ == "__main__":
    main()
