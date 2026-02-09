# backtest_vwap.py
import pandas as pd
import json
import glob
import os

DATA_DIR = 'data/intraday'
INITIAL_CAPITAL = 10000
COMMISSION_RATE = 0.000
STRATEGY_MODE = 1  # 1 = Long only, 2 = Long/Short

def run_backtest():
    json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    if not json_files:
        print(f"No JSON files in {DATA_DIR}")
        return
    results = []
    print(f"{'SYMBOL':<10} {'TRADES':<10} {'WIN_RATE':<10} {'RETURN':<10}")
    print("-" * 45)
    for filepath in json_files:
        symbol = os.path.basename(filepath).split('.')[0].split('_')[1]  # 從 intraday_SYMBOL_date.json 取 SYMBOL
        with open(filepath, 'r') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        if 'close' not in df or 'vwap' not in df:
            continue
        df['signal'] = 0
        df.loc[df['close'] > df['vwap'], 'signal'] = 1
        if STRATEGY_MODE == 2:
            df.loc[df['close'] < df['vwap'], 'signal'] = -1
        df['position'] = df['signal'].shift(1)
        df['market_return'] = df['close'].pct_change()
        df['strategy_return'] = df['position'] * df['market_return']
        df['trades'] = df['position'].diff().abs().fillna(0)
        df['strategy_return_net'] = df['strategy_return'] - (df['trades'] * COMMISSION_RATE)
        df['equity_curve'] = (1 + df['strategy_return_net']).cumprod() * INITIAL_CAPITAL
        total_return = (df['equity_curve'].iloc[-1] / INITIAL_CAPITAL) - 1
        total_trades = df['trades'].sum()
        winning_trades = len(df[df['strategy_return_net'] > 0])
        active_trades = len(df[df['position'] != 0])
        win_rate = (winning_trades / active_trades * 100) if active_trades > 0 else 0
        results.append({'symbol': symbol, 'return': total_return, 'trades': total_trades, 'win_rate': win_rate})
        print(f"{symbol:<10} {int(total_trades):<10} {win_rate:.1f}%     {total_return:.2%}")
    if results:
        df_res = pd.DataFrame(results)
        avg_return = df_res['return'].mean()
        print("-" * 45)
        print(f"AVERAGE RETURN: {avg_return:.2%}")

if __name__ == "__main__":
    run_backtest()