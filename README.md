這是一個為您的交易自動化系統設計的 `README.md` 文檔。這份文檔整合了您提供的所有腳本功能，並以專業的開源項目格式呈現。

***

# 📊 VWAP & Premarket Dashboard

這是一個自動化的美股交易輔助系統，專注於 **VWAP (成交量加權平均價) 分析**、**盤前掃描 (Premarket Scan)** 以及 **期權流動性評分**。系統包含 Python 後端處理腳本、GitHub Actions 自動化流程，以及一個用於數據可視化的 Web 前端儀表板。

## 🚀 主要功能 (Key Features)

### 1. 盤前掃描 (Premarket Scan)
- **腳本**: `premarket_scan.py`
- **功能**:
  - 掃描指定清單 (如 AMD, NVDA, TSLA) 的盤前價格行為。
  - **趨勢分析**: 判斷前一日 VWAP 趨勢 (Bullish/Bearish/Neutral)。
  - **期權評分**: 計算 ATM 期權的成交量 (Volume) 與未平倉量 (OI)，結合 Put/Call Ratio 給出流動性分數 (Liquidity Score)。
  - **情境分類**: 綜合 Gap%、趨勢一致性與期權分數，自動歸類交易情境 (Scenario A/B/C)。
  - **通知**: 自動發送 Telegram 摘要報告。

### 2. 盤後 VWAP 分析 (Post-Market Analysis)
- **腳本**: `vwap_yf.py`
- **功能**:
  - 下載指定日期的 Intraday 分鐘級數據 (使用 `yfinance`)。
  - 計算當日 VWAP 曲線及收盤價乖離率 (Deviation %)。
  - 生成可供前端繪圖的 JSON 數據 (`data/intraday/`)。
  - **通知**: 找出收盤價與 VWAP 偏離最大的前 5 檔股票並發送 Telegram。

### 3. 策略回測 (Backtesting)
- **腳本**: `backtest_vmap.py`
- **功能**:
  - 基於歷史 Intraday 數據回測簡單的 VWAP 策略。
  - **邏輯**: 收盤價 > VWAP 做多，收盤價 < VWAP 做空 (可配置)。
  - **指標**: 計算勝率 (Win Rate)、總報酬 (Return)、最大回撤等關鍵績效指標。

### 4. 網頁儀表板 (Web Dashboard)
- **文件**: `index.html`, `script.js`, `chart.js`
- **功能**:
  - 提供 **盤前掃描** 與 **盤後分析** 兩種檢視模式。
  - 視覺化 K 線圖與 VWAP 曲線。
  - 互動式數據表格，支援查看詳細的期權分數與趨勢數據。

***

## 📂 專案結構 (Project Structure)

```text
.
├── .github/workflows/    # GitHub Actions 自動化配置
│   ├── premarket.yml     # 每日盤前自動掃描流程
│   └── vwap_yf.yml       # 盤後數據更新流程
├── data/                 # 存放生成的 JSON 數據
│   └── intraday/         # 分鐘級 K 線數據 (供圖表使用)
├── backtest_vmap.py      # VWAP 策略回測腳本
├── premarket_scan.py     # 盤前掃描主程式
├── vwap_yf.py            # VWAP 計算與數據下載
├── telegram_utils.py     # Telegram 機器人工具庫
├── index.html            # 儀表板入口網頁
├── script.js             # 前端主要邏輯
├── chart.js              # 圖表繪製邏輯
└── requirements.txt      # Python 依賴套件
```

***

## 🛠️ 安裝與使用 (Installation & Usage)

### 1. 環境設定
確保已安裝 Python 3.11+，並安裝所需套件：

```bash
pip install -r requirements.txt
```

### 2. 配置 Telegram 通知 (可選)
在環境變數或 GitHub Secrets 中設定：
- `TG_BOT_TOKEN`: 您的 Telegram Bot Token
- `TG_CHAT_ID`: 接收訊息的 Chat ID

### 3. 執行腳本

**執行盤前掃描:**
```bash
# 掃描指定代碼
python premarket_scan.py "AMD,NVDA,TSLA,AAPL,SMCI"
```

**執行 VWAP 分析:**
```bash
# 計算指定日期 (YYYY-MM-DD) 的 VWAP
python vwap_yf.py 2024-02-02 "AMD,NVDA" 5m
```

**執行回測:**
```bash
python backtest_vmap.py
```

### 4. 啟動儀表板
直接在瀏覽器中打開 `index.html` 即可載入 `data/` 目錄下的 JSON 數據進行分析。

***

## 🤖 自動化 (Automation)

本專案包含 GitHub Actions 工作流，可實現完全自動化：

- **Premarket Scan**: 每日 UTC 13:00 (美股盤前) 自動執行掃描並更新數據庫 。
- **Git Integration**: 掃描結果會自動 Commit 並 Push 回儲存庫，確保網頁端看到的數據永遠是最新的。

***

## 📊 策略邏輯摘要 (Strategy Logic)

| 指標 | 說明 |
| :--- | :--- |
| **Liquidity Score** | 基於 ATM 選項的 Volume 分級 (0-3 分)。 |
| **Flow Score** | 綜合考慮總 Volume、Open Interest 及 Put/Call Ratio。 |
| **Scenario A** | 高分 setups (Total Score ≥ 6)，通常伴隨顯著 Gap 或一致的趨勢。 |
| **Scenario C** | 低分 setups (Total Score ≤ 2)，建議觀望或輕倉。 |
