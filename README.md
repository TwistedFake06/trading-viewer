# 📊 VWAP 盤後小工具（yfinance / JSON + 前端檢視）

這個專案每天自動抓取美股 1 分鐘資料，計算各股票的全日 VWAP，輸出成 JSON，並提供一個簡單的前端頁面，方便盤後快速檢視與複製 Markdown 筆記。 [web:137]

---

## 功能總覽

- 使用 GitHub Actions 定時抓取美股 1 分鐘資料（yfinance）。 [web:137]
- 依自訂 watchlist 計算每天的收盤價、VWAP 與收盤相對 VWAP 百分比。 [web:139]
- 將結果存成 `data/vwap_YYYY-MM-DD.json`。 [web:139]
- 透過靜態前端（`index.html` + `script.js`）載入 JSON，產生表格與可直接貼到筆記的 Markdown 段落。 [web:137]

---

## 專案結構

```text
.
├── .github/
│   └── workflows/
│       └── vwap.yml          # GitHub Actions：排程與手動執行 VWAP 計算
├── data/
│   └── vwap_YYYY-MM-DD.json  # 每日 VWAP 結果（盤後計算輸出）
├── src/                      # Python 計算腳本
│   ├── main.py               # 入口：讀 watchlist、呼叫 yfinance、計算 VWAP
│   ├── vwap_calc.py          # VWAP 計算邏輯與輔助函式
│   └── config.py             # 設定：watchlist、時間區間等
├── index.html                # 前端頁面：表單 + 結果表格 + Markdown 輸出
├── script.js                 # 前端邏輯：載入 JSON、渲染 Scenario 與 Markdown
└── README.md                 # 本文件
