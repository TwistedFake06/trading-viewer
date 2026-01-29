// 使用 StockData.org 取得 intraday 1 分鐘 K，並計算當日 VWAP [web:39][web:64]

async function fetchIntradayDataFromStockData(symbol, apiKey) {
  // interval 可改成 5min/15min，看你需要；這裡先用 1min [web:39]
  const url =
    `https://api.stockdata.org/v1/data/intraday?symbols=${encodeURIComponent(symbol)}&interval=1min&api_token=${encodeURIComponent(apiKey)}`;

  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`HTTP 錯誤：${resp.status}`);
  }

  const json = await resp.json();

  // StockData.org 會把 K 線放在 json.data 陣列裡 [web:39]
  if (!json || !Array.isArray(json.data)) {
    throw new Error("回傳格式異常，找不到 data 陣列。");
  }

  return json.data;
}

// 過濾出指定日期的所有 1 分鐘 K
function filterByDate(data, targetDateStr) {
  return data.filter(bar => {
    // StockData 的日期通常是 ISO 字串，例如 "2026-01-28T15:59:00-05:00" [web:39]
    const d = bar.date.split("T")[0];
    return d === targetDateStr;
  });
}

// 計算當日全日 VWAP 與收盤價
function calcVWAPAndClose(bars) {
  if (!bars || bars.length === 0) {
    throw new Error("找不到這一天的 1 分鐘 K。請確認日期為交易日，且 API 有回傳資料。");
  }

  // 確保按時間排序
  const sorted = [...bars].sort((a, b) => new Date(a.date) - new Date(b.date));

  let pvSum = 0;
  let volSum = 0;

  sorted.forEach(bar => {
    const high = Number(bar.high);
    const low = Number(bar.low);
    const volume = Number(bar.volume);
    if (!isFinite(high) || !isFinite(low) || !isFinite(volume)) return;

    const typicalPrice = (high + low) / 2;
    pvSum += typicalPrice * volume;
    volSum += volume;
  });

  if (volSum === 0) {
    throw new Error("當日成交量為 0 或資料異常，無法計算 VWAP。");
  }

  const vwap = pvSum / volSum;
  const lastBar = sorted[sorted.length - 1];
  const close = Number(lastBar.close);

  return { vwap, close, lastBarTime: lastBar.date };
}

// A/B/C 規則
function decideScenario(vwap, close) {
  const diff = close - vwap;
  const pct = (diff / vwap) * 100;

  let scenario;
  if (pct > 0.5) {
    scenario = "A（偏多：收盤在 VWAP 明顯上方）";
  } else if (pct < -0.5) {
    scenario = "B（偏空：收盤在 VWAP 明顯下方）";
  } else {
    scenario = "C（中性：收盤貼近 VWAP）";
  }

  return { pct, scenario };
}

// 顯示結果
function renderResult(symbol, dateStr, vwap, close, pct, scenario, lastBarTime) {
  const resultDiv = document.getElementById("result");
  resultDiv.style.display = "block";

  const pctStr = pct.toFixed(2);
  const vwapStr = vwap.toFixed(4);
  const closeStr = close.toFixed(4);

  const markdownSnippet =
`### ${symbol}（${dateStr}）盤後 VWAP 快速紀錄

- 收盤價：${closeStr}
- 全日 VWAP：${vwapStr}
- 收盤相對 VWAP：${pctStr}%（${pct > 0 ? "在上方" : pct < 0 ? "在下方" : "幾乎一樣"}）
- Scenario：${scenario}

> 備註：目前只根據 VWAP 一個維度判斷 A/B/C，之後可加上量能、Volume Profile、Options Flow。`;

  resultDiv.innerHTML = `
    <table>
      <tr><th>Ticker</th><th>日期</th><th>收盤</th><th>VWAP</th><th>收盤-VWAP%</th><th>Scenario</th></tr>
      <tr>
        <td>${symbol}</td>
        <td>${dateStr}</td>
        <td>${closeStr}</td>
        <td>${vwapStr}</td>
        <td>${pctStr}%</td>
        <td>${scenario}</td>
      </tr>
    </table>
    <p style="margin-top:8px;font-size:12px;color:#666;">最後一根 K 時間（StockData 資料）：${lastBarTime}</p>
    <p style="margin-top:12px;font-size:14px;">以下為可直接貼到你的盤後筆記的 Markdown：</p>
    <pre style="white-space:pre-wrap;font-size:12px;border:1px solid #ddd;border-radius:4px;padding:8px;background:#fafafa;">${markdownSnippet}</pre>
  `;
}

// 綁定按鈕
document.getElementById("runBtn").addEventListener("click", async () => {
  const symbol = document.getElementById("symbol").value.trim().toUpperCase();
  const dateStr = document.getElementById("date").value.trim();
  const apiKey = document.getElementById("apiKey").value.trim();

  const errorDiv = document.getElementById("error");
  const resultDiv = document.getElementById("result");
  errorDiv.textContent = "";
  resultDiv.style.display = "none";

  if (!symbol || !dateStr || !apiKey) {
    errorDiv.textContent = "請先填寫 Ticker、日期與 StockData API Key。";
    return;
  }

  try {
    const raw = await fetchIntradayDataFromStockData(symbol, apiKey); // [web:39][web:64]
    const dayBars = filterByDate(raw, dateStr);
    const { vwap, close, lastBarTime } = calcVWAPAndClose(dayBars);
    const { pct, scenario } = decideScenario(vwap, close);
    renderResult(symbol, dateStr, vwap, close, pct, scenario, lastBarTime);
  } catch (e) {
    console.error(e);
    errorDiv.textContent = "出錯了：" + e.message;
  }
});
