import pandas as pd
import json
import glob
import os

# --- Configuration ---
DATA_DIR = 'data/intraday'
INITIAL_CAPITAL = 10000
COMMISSION_RATE = 0.000  # 0.001 for 0.1% per trade
# Strategy: 1 = Long only, 2 = Long/Short
STRATEGY_MODE = 1 

def run_backtest():
    json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    
    if not json_files:
        print(f"❌ No JSON files found in {DATA_DIR}")
        return

    results = []

    print(f"{'SYMBOL':<10} {'TRADES':<10} {'WIN_RATE':<10} {'RETURN':<10}")
    print("-" * 45)

    for filepath in json_files:
        symbol = os.path.basename(filepath).split('.')[0]
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Ensure required columns exist
            required_cols = {'close', 'vwap'}
            if not required_cols.issubset(df.columns):
                continue
            
            # 1. Generate Signals
            # Long (1) if Close > VWAP, Short (-1) if Close < VWAP, else 0
            df['signal'] = 0
            df.loc[df['close'] > df['vwap'], 'signal'] = 1
            if STRATEGY_MODE == 2:
                df.loc[df['close'] < df['vwap'], 'signal'] = -1
            
            # 2. Calculate Returns
            # Shift signal by 1 because today's signal executes tomorrow/next bar
            df['position'] = df['signal'].shift(1)
            df['market_return'] = df['close'].pct_change()
            df['strategy_return'] = df['position'] * df['market_return']
            
            # 3. Calculate Transaction Costs
            # Count whenever position changes (e.g., 0 to 1, 1 to -1)
            df['trades'] = df['position'].diff().abs().fillna(0)
            df['strategy_return_net'] = df['strategy_return'] - (df['trades'] * COMMISSION_RATE)
            
            # 4. Cumulative Metrics
            df['equity_curve'] = (1 + df['strategy_return_net']).cumprod() * INITIAL_CAPITAL
            
            total_return = (df['equity_curve'].iloc[-1] / INITIAL_CAPITAL) - 1
            total_trades = df['trades'].sum()
            
            # Calculate Win Rate (positive return bars / total active bars)
            winning_trades = len(df[df['strategy_return_net'] > 0])
            active_trades = len(df[df['position'] != 0])
            win_rate = (winning_trades / active_trades * 100) if active_trades > 0 else 0

            results.append({
                'symbol': symbol,
                'return': total_return,
                'trades': total_trades,
                'win_rate': win_rate
            })

            print(f"{symbol:<10} {int(total_trades):<10} {win_rate:.1f}%     {total_return:.2%}")

        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    # Portfolio Summary
    if results:
        df_res = pd.DataFrame(results)
        avg_return = df_res['return'].mean()
        print("-" * 45)
        print(f"AVERAGE PORTFOLIO RETURN: {avg_return:.2%} [cite:code_file:1]")

if __name__ == "__main__":
    run_backtest()
