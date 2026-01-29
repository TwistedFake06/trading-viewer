import sys
import json
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

def calc_vwap_for_symbol(symbol: str, date_str: str, interval: str = "1m", max_retry_days: int = 7):
    """
    使用 yfinance 取得某一檔股票在指定日期的 intraday 資料，
    計算當日 VWAP、收盤價與收盤相對 VWAP 的百分比。
    
    如果指定日期無資料，會自動往前找最多 max_retry_days 天。
    
    Args:
        symbol: 股票代碼
        date_str: 日期字串 YYYY-MM-DD
        interval: K 線週期，預設 "1m"，也可用 "5m"
        max_retry_days: 最多往前找幾天（預設 7 天，涵蓋週末）
    """
    date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    # 最多往前找 max_retry_days 天
    for days_ago in range(max_retry_days + 1):
        current_date = date - timedelta(days=days_ago)
        next_date = current_date + timedelta(days=1)
        
        if days_ago > 0:
            print(f"[INFO] {symbol} {date_str} 無資料，嘗試 {current_date.strftime('%Y-%m-%d')} (往前 {days_ago} 天)")
        else:
            print(f"[DEBUG] Downloading {symbol} {current_date.strftime('%Y-%m-%d')} {interval} data ...")
        
        df = yf.download(
            symbol,
            interval=interval,
            start=current_date.strftime("%Y-%m-%d"),
            end=next_date.strftime("%Y-%m-%d"),
            progress=False
        )
        
        # 只在第一次嘗試印詳細 debug
        if days_ago == 0:
            print(f"[DEBUG] df type: {type(df)}")
            print(f"[DEBUG] df.head():\n{df.head()}")
            print(f"[DEBUG] df.shape = {df.shape}, rows = {len(df)}")
            print(f"[DEBUG] df.columns: {list(df.columns)}")
        
        if df.empty:
            if days_ago < max_retry_days:
                continue  # 試下一天
            else:
                print(f"[WARN] {symbol} 往前找 {max_retry_days} 天都無資料，跳過。")
                return None
        
        # 有資料，開始計算 VWAP
        # 處理 MultiIndex 欄位：('Close','AMD') 這一類
        if isinstance(df.columns, pd.MultiIndex):
            close_col = ("Close", symbol)
            high_col = ("High", symbol)
            low_col = ("Low", symbol)
            vol_col = ("Volume", symbol)
        else:
            close_col = "Close"
            high_col = "High"
            low_col = "Low"
            vol_col = "Volume"
        
        # 確保必要欄位存在
        missing = []
        for col in [close_col, high_col, low_col, vol_col]:
            if col not in df.columns:
                missing.append(col)
        
        if missing:
            print(f"[WARN] {symbol} {current_date.strftime('%Y-%m-%d')} 缺少欄位 {missing}，跳過。")
            if days_ago < max_retry_days:
                continue
            else:
                return None
        
        high = df[high_col]
        low = df[low_col]
        vol = df[vol_col]
        
        if days_ago == 0:
            print(f"[DEBUG] Volume sample for {symbol}:\n{vol.head()}")
            print(f"[DEBUG] Volume dtype for {symbol}: {vol.dtype}")
        
        tp = (high + low) / 2.0
        pv = tp * vol
        
        vol_sum_raw = vol.sum()
        vol_sum = float(vol_sum_raw)
        
        if vol_sum == 0.0:
            print(f"[WARN] {symbol} {current_date.strftime('%Y-%m-%d')} 成交量總和為 0")
            if days_ago < max_retry_days:
                continue
            else:
                print(f"[WARN] {symbol} 往前找 {max_retry_days} 天都沒有成交量，跳過。")
                return None
        
        vwap = float(pv.sum()) / vol_sum
        close = float(df[close_col].iloc[-1])
        pct = (close - vwap) / vwap * 100.0
        
        actual_date_used = current_date.strftime("%Y-%m-%d")
        
        if days_ago > 0:
            print(f"[INFO] {symbol} 使用 {actual_date_used} 的資料（往前 {days_ago} 天）")
        
        return {
            "symbol": symbol,
            "date": actual_date_used,  # 使用實際有資料的日期
            "close": round(close, 4),
            "vwap": round(vwap, 4),
            "close_vwap_pct": round(pct, 4)
        }
    
    # 理論上不會到這裡（上面 for loop 已經處理）
    return None

def main():
    """
    用法：
      python vwap_yf.py YYYY-MM-DD AMD,NVDA,TSLA [interval]
    
    輸出：
      data/vwap_YYYY-MM-DD.json
    
    內容為多檔股票的列表：
      [
        {"symbol": "...", "date": "...", "close": ..., "vwap": ..., "close_vwap_pct": ...},
        ...
      ]
    
    如果指定日期無資料（例如週末、盤前），會自動往前找最多 7 天。
    """
    if len(sys.argv) < 3:
        print("Usage: python vwap_yf.py YYYY-MM-DD AMD,NVDA,TSLA [interval]", file=sys.stderr)
        print("  interval: 1m (default) or 5m", file=sys.stderr)
        sys.exit(1)
    
    date_str = sys.argv[1]
    symbols_str = sys.argv[2]
    interval = sys.argv[3] if len(sys.argv) > 3 else "1m"
    
    symbols = [s.strip().upper() for s in symbols_str.split(",") if s.strip()]
    
    results = []
    for sym in symbols:
        print(f"[INFO] Processing {sym} {date_str} ...")
        try:
            res = calc_vwap_for_symbol(sym, date_str, interval=interval, max_retry_days=7)
        except Exception as e:
            print(f"[ERROR] {sym} {date_str} 計算失敗：{e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            continue
        
        if res is not None:
            results.append(res)
    
    if not results:
        print("[WARN] 此日期／標的組合沒有任何可用結果。")
        return
    
    import os
    os.makedirs("data", exist_ok=True)
    out_path = f"data/vwap_{date_str}.json"
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"[INFO] Wrote {out_path} with {len(results)} records")

if __name__ == "__main__":
    main()
