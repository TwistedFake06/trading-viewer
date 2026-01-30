import sys
import json
import os
import traceback
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------
# Helper: Robust Column Mapping
# ---------------------------------------------------------
def find_columns(df):
    """
    自動尋找 DataFrame 中對應 Open/High/Low/Close/Volume 的欄位名稱。
    不論是 MultiIndex 還是單層 Index，不論大小寫，都能抓到。
    回傳一個 dict: {'open': col_name, 'high': col_name, ...}
    """
    mapping = {}
    required = ['open', 'high', 'low', 'close', 'volume']
    
    # 遍歷所有欄位，尋找關鍵字
    for col in df.columns:
        # 如果是 MultiIndex (Tuple)，就把所有層級轉成字串合併搜尋
        # 如果是 SingleIndex (String)，直接搜尋
        col_str = str(col).lower()
        
        # 檢查是否包含關鍵字 (精確匹配比較安全，避免 'Adj Close' 混淆)
        # 對於 MultiIndex，通常是 ('Close', 'AMD') 這樣的 tuple
        
        parts = []
        if isinstance(col, tuple):
            parts = [str(p).lower() for p in col]
        else:
            parts = [str(col).lower()]
            
        for p in parts:
            if p == 'open': mapping['open'] = col
            elif p == 'high': mapping['high'] = col
            elif p == 'low': mapping['low'] = col
            elif p == 'volume': mapping['volume'] = col
            elif p == 'close': 
                # 排除 Adj Close，除非只有 Adj Close
                # 這裡簡單處理：只要是 Close 就先抓，如果有更精確的再說
                # yfinance 通常回傳 'Close' 和 'Adj Close'
                # 我們優先找完全等於 'close' 的 part
                mapping['close'] = col

    # 檢查是否缺欄位
    missing = [k for k in required if k not in mapping]
    if missing:
        return None, f"Missing columns: {missing}"
        
    return mapping, None

# ---------------------------------------------------------
# Helper: Save Intraday Data for Charting
# ---------------------------------------------------------
def save_intraday_data(df, symbol, date_str):
    """
    將 DataFrame 轉成前端 Lightweight Charts 需要的格式並存檔
    格式: [{time, open, high, low, close, volume, vwap}, ...]
    """
    try:
        # 1. 取得欄位對映
        col_map, err = find_columns(df)
        if err:
            print(f"[WARN] Skip chart for {symbol}: {err}")
            return

        # 2. 複製並重命名標準欄位
        temp_df = df.rename(columns={
            col_map['open']: 'open',
            col_map['high']: 'high',
            col_map['low']: 'low',
            col_map['close']: 'close',
            col_map['volume']: 'volume'
        }).copy()
        
        # 只留需要的欄位
        temp_df = temp_df[['open', 'high', 'low', 'close', 'volume']]
        
        # 3. 計算 Intraday VWAP Curve
        # VWAP = Cumulative(Price * Volume) / Cumulative(Volume)
        # 這裡用典型價格 (High+Low+Close)/3
        temp_df['tp'] = (temp_df['high'] + temp_df['low'] + temp_df['close']) / 3
        temp_df['pv'] = temp_df['tp'] * temp_df['volume']
        
        temp_df['cum_pv'] = temp_df['pv'].cumsum()
        temp_df['cum_vol'] = temp_df['volume'].cumsum()
        
        # 避開除以零
        temp_df['vwap'] = temp_df['cum_pv'] / temp_df['cum_vol'].replace(0, 1)
        
        # 4. 轉 List of Dict (Lightweight Charts 格式)
        chart_data = []
        for idx, row in temp_df.iterrows():
            # Index 是 Datetime
            ts = int(idx.timestamp())
            
            # 簡單防呆：過濾掉 Volume=0 且價格沒動的數據(選擇性)
            # 這裡保留所有數據
            
            chart_data.append({
                "time": ts,
                "open": round(row['open'], 2),
                "high": round(row['high'], 2),
                "low": round(row['low'], 2),
                "close": round(row['close'], 2),
                "volume": int(row['volume']),
                "vwap": round(row['vwap'], 2)
            })
            
        # 5. 存檔
        dir_path = "data/intraday"
        os.makedirs(dir_path, exist_ok=True)
        file_path = f"{dir_path}/intraday_{symbol}_{date_str}.json"
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(chart_data, f)
            
        print(f"[INFO] Saved chart data: {file_path} ({len(chart_data)} bars)")
        
    except Exception as e:
        print(f"[WARN] Failed to save intraday data for {symbol}: {e}")
        # traceback.print_exc() # Debug 用

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
            # 下載資料
            # auto_adjust=False 確保我們拿到原始的 Open/High/Low/Close
            # multi_level_index=False 嘗試強制單層索引 (yfinance 新版參數，舊版可能忽略)
            df = yf.download(
                symbol,
                interval=interval,
                start=actual_date_str,
                end=next_date.strftime("%Y-%m-%d"),
                progress=False,
                auto_adjust=False 
            )
        except Exception as e:
            print(f"[WARN] Download failed for {symbol}: {e}")
            continue
        
        if df.empty:
            if days_ago < max_retry_days: continue
            else:
                print(f"[WARN] {symbol} 往前找 {max_retry_days} 天都無資料，跳過。")
                return None
        
        # --- 抓取欄位 ---
        col_map, err = find_columns(df)
        if err:
            print(f"[WARN] {symbol} column error: {err}")
            if days_ago < max_retry_days: continue
            return None
            
        # --- 存圖表資料 (Intraday JSON) ---
        save_intraday_data(df, symbol, actual_date_str)
        
        # --- 計算 Summary VWAP ---
        # 使用對映好的欄位名稱取值
        high = df[col_map['high']]
        low = df[col_map['low']]
        vol = df[col_map['volume']]
        close_series = df[col_map['close']]
        
        vol_sum = float(vol.sum())
        if vol_sum == 0.0:
            print(f"[WARN] {symbol} Vol=0")
            if days_ago < max_retry_days: continue
            return None
            
        tp = (high + low) / 2.0
        pv = tp * vol
        vwap = float(pv.sum()) / vol_sum
        
        # 取最後一筆收盤價
        close = float(close_series.iloc[-1])
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
            traceback.print_exc()
            
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
