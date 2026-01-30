# 📊 VWAP & Premarket Trading Dashboard

這是一個全自動的美股交易輔助工具，整合了 **盤後 VWAP 分析** 與 **盤前策略掃描**。利用 GitHub Actions 自動抓取資料，並透過靜態網頁 (GitHub Pages) 提供互動式圖表與 Markdown 筆記生成。

![Dashboard Preview](https://via.placeholder.com/800x400?text=Dashboard+Preview) <!-- 你可以之後換成真的截圖 -->

## 🚀 主要功能

### 1. 📉 盤後 VWAP 分析 (After Hours Analysis)
- **自動計算**：每日收盤後自動抓取當日 5 分鐘 K 線 (5m Intraday)。
- **VWAP 策略**：計算全日 VWAP，並根據收盤價相對位置判斷多空 (Scenario A/B/C)。
- **智能回退**：若當日無資料（如週末或休市），自動往前尋找最近一個交易日。
- **輸出筆記**：一鍵生成可直接貼到 Obsidian / Notion 的 Markdown 格式筆記。

### 2. 🚀 盤前掃描 (Premarket Scan)
- **盤前快篩**：在美股開盤前 (Pre-market) 掃描 Watchlist。
- **多維度評分**：綜合「昨日趨勢」、「盤前漲跌幅」、「期權流動性」進行打分。
- **重點標記**：自動標示高分標的與異常波動股。

### 3. 🕯️ 互動式圖表 (Intraday Charts)
- **K 線圖**：整合 TradingView Lightweight Charts，支援 5m K 線。
- **技術指標**：
  - **VWAP** (成交量加權平均價) 黃色線。
  - **Volume** (成交量) 底部柱狀圖，綠漲紅跌。
- **即點即看**：在儀表板點擊任一 Ticker 即可跳轉至該檔股票的詳細走勢圖。

---

## 🛠️ 專案結構

```text
.
├── .github/workflows/
│   ├── vwap_yf.yml         # [排程] 盤後 VWAP 計算 (自動重試 + 5m K線)
│   └── premarket.yml       # [排程] 盤前掃描策略
├── data/
│   ├── vwap_YYYY-MM-DD.json       # 每日盤後 Summary
│   ├── premarket_YYYY-MM-DD.json  # 每日盤前 Scan 結果
│   └── intraday/                  # 詳細 K 線數據 (供圖表用)
├── src/
│   ├── vwap_yf.py          # 核心計算：VWAP、Intraday Data、自動回退邏輯
│   └── premarket_scan.py   # 盤前邏輯：昨收、盤前漲跌、期權評分
├── index.html              # 主儀表板 (Dashboard)
├── chart.html              # K 線圖表頁面
├── script.js               # 前端邏輯 (載入 JSON、渲染表格、Markdown 生成)
├── chart.js                # 圖表邏輯 (Lightweight Charts 繪圖)
└── requirements.txt        # Python 依賴 (yfinance, pandas, etc.)
