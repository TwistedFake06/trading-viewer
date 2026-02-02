name: VWAP with yfinance

on:
  schedule:
    # 每天 11:00 UTC（香港 19:00 左右），計算前一天 VWAP
    - cron: '0 11 * * *'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  vwap:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Compute VWAP for watchlist
        env:
          TG_BOT_TOKEN: ${{ secrets.TG_BOT_TOKEN }}
          TG_CHAT_ID: ${{ secrets.TG_CHAT_ID }}
        run: |
          # 使用「前一天（UTC）」作為目標日期
          DATE=$(date -u -d '1 day ago' +'%Y-%m-%d')
          echo "Target date: $DATE"
          python vwap_yf.py "$DATE" "AMD,NVDA,TSLA,AAPL,SMCI,MSFT,ONDS,RGTI,MU,SNDK,AVGO,INTC,QUBT" "5m"

      - name: Commit VWAP JSON
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

          git add data/ || echo "no data dir"
          git commit -m "Update VWAP data (watchlist)" || echo "No changes to commit"

          # 與遠端 main 對齊，避免 non-fast-forward
          git fetch origin main
          git rebase origin/main || echo "rebase failed or nothing to rebase"

          git push origin HEAD:main || echo "push failed (maybe no new commits)"
