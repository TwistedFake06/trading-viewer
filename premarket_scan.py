import sys
import json
import traceback
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def get_last_trading_day_vwap(symbol, interval="5m"):
    """抓過去 7 天內最近一個完整交易日的 VWAP 狀態"""
    date = datetime.now().date()
    for i in range(1, 8): 
        target_date = date - timedelta(days=i)
        start_str = target_date.strftime("%Y-%m-%d")
        end_str = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
        
        try:
            df = yf.download(symbol, interval=interval, start=start_str, end=end_str, progress=False)
            if df.empty or len(df) < 10: continue
            
            # 欄位處理
            if isinstance(df.columns, pd.MultiIndex):
                close_col, high_col, low_col, vol_col = ("Close", symbol), ("High", symbol), ("Low", symbol), ("Volume", symbol)
            else:
                close_col, high_col, low_col, vol_col = "Close", "High", "Low", "Volume"

            if vol_col not in df.columns: continue
            
            high, low, vol = df[high_col], df[low_col], df[vol_col]
            tp = (high + low) / 2.0
            pv = tp * vol
            vwap = pv.sum() / vol.sum()
            close = float(df[close_col].iloc[-1])
            
            pct = (close - vwap) / vwap * 100.0
            trend = "Bullish" if pct > 0.3 else ("Bearish" if pct < -0.3 else "Neutral")
            
            return {"date": start_str, "prev_close": close, "prev_vwap": float(vwap), "prev_trend": trend}
        except:
            continue
    return None

def get_premarket_data(symbol):
    """抓盤前價格"""
    try:
        tick = yf.Ticker(symbol)
        price = tick.fast_info.last_price
        prev_close = tick.fast_info.previous_close
        change_pct = ((price - prev_close) / prev_close * 100.0) if prev_close else 0.0
        return {"price": float(price), "change_pct": float(change_pct)}
    except:
        return None

def get_options_score(symbol):
    """簡易期權流動性評分 (0-3分)"""
    try:
        tick = yf.Ticker(symbol)
        if not tick.options: return 0
        
        chain = tick.option_chain(tick.options[0]) # 最近到期日
        calls = chain.calls
        price = tick.fast_info.last_price
        
        # 只看 ATM 附近
        calls = calls[(calls['strike'] >= price * 0.95) & (calls['strike'] <= price * 1.05)]
        vol = calls['volume'].sum()
        
        if vol > 5000: return 3
        if vol > 1000: return 2
        if vol > 100: return 1
        return 0
    except:
        return 0

# ---------------------------------------------------------
# Main Logic
# ---------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python premarket_scan.py SYMBOLS")
        sys.exit(1)
        
    symbols = [s.strip().upper() for s in sys.argv[1].split(",") if s.strip()]
    results = []
    
    print(f"Scanning {len(symbols)} symbols...")
    
    for sym in symbols:
        try:
            # 1. 昨勢
            prev = get_last_trading_day_vwap(sym) or {"prev_trend": "N/A", "prev_close": 0}
            
            # 2. 盤前
            pre = get_premarket_data(sym)
            if not pre: pre = {"price": prev["prev_close"], "change_pct": 0.0}
            
            # 3. 期權
            opt_score = get_options_score(sym)
            
            # 4. 算分
            total_score = opt_score
            if abs(pre["change_pct"]) > 1.5: total_score += 2
            elif abs(pre["change_pct"]) > 0.5: total_score += 1
            if prev["prev_trend"] == "Bullish" and pre["change_pct"] > 0: total_score += 1
            
            results.append({
                "symbol": sym,
                "prev_trend": prev["prev_trend"],
                "price": pre["price"],
                "change_pct": pre["change_pct"],
                "opt_score": opt_score,
                "total_score": total_score
            })
            print(f" - {sym}: Score {total_score}")
            
        except Exception as e:
            print(f"Error {sym}: {e}")

    # 輸出 JSON
    today = datetime.now().strftime("%Y-%m-%d")
    import os
    os.makedirs("data", exist_ok=True)
    with open(f"data/premarket_{today}.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)

if __name__ == "__main__":
    main()
