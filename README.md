# 📊 VWAP & Premarket Dashboard

美股交易輔助系統，專注 VWAP 分析、盤前掃描與期權評分。包含 Python 後端、GitHub Actions 自動化與 Web 前端。

## 主要功能

1. **盤前掃描**: `premarket_scan.py` - VWAP 趨勢、盤前價、期權分數、Telegram 通知。
2. **VWAP 分析**: `vwap_yf.py` - Intraday 數據計算 VWAP，生成 JSON。
3. **回測**: `backtest_vwap.py` - VWAP 策略回測。
4. **儀表板**: `index.html` / `chart.html` - 視覺化表格與圖表。

## 結構

.
├── .github/workflows/ # Actions
│ ├── premarket.yml
│ └── vwap_yf.yml
├── data/ # JSON 數據
├── utils.py # 共同工具 (VWAP, Telegram)
├── premarket_scan.py
├── vwap_yf.py
├── backtest_vwap.py
├── index.html # 儀表板
├── chart.html # 圖表頁
├── script.js # 前端邏輯
├── chart.js # 圖表邏輯
└── requirements.txt

## 安裝

```bash
pip install -r requirements.txt
```

設定 TG_BOT_TOKEN / TG_CHAT_ID 環境變數。
使用

盤前: python premarket_scan.py AMD,NVDA
VWAP: python vwap_yf.py 2024-02-02 AMD,NVDA --interval 5m
回測: python backtest_vwap.py
儀表板: 開啟 index.html
優化記錄

提取共同邏輯到 utils.py。
批量 yfinance，提高效率。
JS 表格支援排序。
Actions 簡化日期處理。

這些是優化後的完整檔案。如果需要測試特定腳本或進一步修改，請告訴我！ 😄
