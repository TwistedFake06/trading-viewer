// Debug logger：把訊息印到頁面下方的 <pre id="debug">
function logDebug(message, obj) {
  const debugEl = document.getElementById("debug");
  const time = new Date().toISOString();
  let line = "[" + time + "] " + message;
  if (obj !== undefined) {
    try {
      line += " " + JSON.stringify(obj, null, 2);
    } catch (e) {
      line += " (JSON stringify error)";
    }
  }
  debugEl.textContent += line + "\n";
}

function clearDebug() {
  const debugEl = document.getElementById("debug");
  debugEl.textContent = "";
}

// 使用 StockData.org 的 intraday endpoint 取得分鐘線 [file:2]
async function fetchIntradayDataFromStockData(symbol, apiKey, targetDateStr) {
  // interval=minute，date=YYYY-MM-DD
  const url =
    "https://api.stockdata.org/v1/data/intraday" +
    "?symbols=" + encodeURIComponent(symbol) +
    "&interval=minute" +
    "&date=" + encodeURIComponent(targetDateStr) +
    "&api_token=" + encodeURIComponent(apiKey);

  logDebug("Request URL:", url);

  const resp = await fetch(url);
  logDebug("HTTP status:", { status: resp.status, statusText: resp.statusText });

  let textBody = "";
  try {
    textBody = await resp.text();
  } catch (e) {
    textBody = "";
  }
  logDebug("Raw response text (truncated):", textBody.slice(0, 500));

  if (!resp.ok) {
    try {
      const errJson = JSON.parse(textBody);
      logDebug("Error JSON:", errJson);
      if (errJson.error) {
        throw new Error("StockData 錯誤：" + errJson.error.code + " - " + errJson.error.message);
      }
    } catch (e) {
      // 不是 JSON 就略過
    }
    throw new Error("HTTP 錯誤：" + resp.status);
  }

  let json;
  try {
    json = textBody ? JSON.parse(textBody) : {};
  } catch (e) {
    logDebug("JSON parse error:", e.message);
    throw new Error("回傳不是合法 JSON。");
  }

  logDebug("JSON meta/sample:", {
    meta: json.meta,
    sample: json.data ? json.data.slice(0, 3) : null
  });

  if (json.error) {
    throw new Error("StockData 錯誤：" + json.error.code + " - " + json.error.message);
  }
  if (!json || !Array.isArray(json.data)) {
    throw new Error("回傳格式異常，找不到 data 陣列。");
  }

  return json.data;
}

// 再保險過濾一次日期
function filterByDate(data, targetDateStr) {
  const filtered = data.filter(function (bar) {
    if (!bar.date) return false;
    const d = bar.date.split("T")[0];
    return d === targetDateStr;
  });
  logDebug("Bars after date filter:", { count: filtered.length });
  return filtered;
}

// 計算當日全日 VWAP 與收盤價
function calcVWAPAndClose(bars) {
  if (!bars || bars.length === 0) {
    throw new Error("找不到這一天的 K 線資料。請確認日期為交易日，且 API 有回傳資料。");
  }

  const sorted = bars.slice().sort(function (a, b) {
    return new Date(a.date) - new Date(b.date);
  });

  let pvSum = 0;
  let volSum = 0;

  sorted.forEach(function (bar) {
    // intraday 結構：bar.data.open/high/low/close/volume [file:2]
    const data = bar.data || bar;
    const high = Number(data.high);
    const low = Number(data.low);
    const volume = Number(data.volume);
    if (!isFinite(high) || !isFinite(low) || !isFinite(volume)) return;

    const typicalPrice = (high + low) / 2;
    pvSum += typicalPrice * volume;
    volSum += volume;
  });

  logDebug("VWAP calc summary:", { pvSum: pvSum, volSum: volSum });

  if (volSum === 0) {
    throw new Error("當日成交量為 0 或資料異常，無法計算 VWAP。");
  }

  const vwap = pvSum / volSum;
  const lastBar = sorted[sorted.length - 1];
  const lastData = lastBar.data || lastBar;
  const close = Number(lastData.close);

  logDebug("VWAP & close:", { vwap: vwap, close: close, lastBarTime: lastBar.date });

  return { vwap: vwap, close: close, lastBarTime: lastBar.date };
}

// Scenario A/B/C 判斷
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

  logDebug("Scenario decision:", { diff: diff, pct: pct, scenario: scenario });

  return { pct: pct, scenario: scenario };
}

// 顯示結果
function renderResult(symbol, dateStr, vwap, close, pct, scenario, lastBarTime) {
  const resultDiv = document.getElementById("result");
  resultDiv.style.display = "block";

  const pctStr = pct.toFixed(2);
  const vwapStr = vwap.toFixed(4);
  const closeStr = close.toFixed(4);

  const markdownSnippet =
"### " + symbol + "（" + dateStr + "）盤後 VWAP 快速紀錄\n\n" +
"- 收盤價：" + closeStr + "\n" +
"- 全日 VWAP：" + vwapStr + "\n" +
"- 收盤相對 VWAP：" + pctStr + "%（" +
  (pct > 0 ? "在上方" : (pct < 0 ? "在下方" : "幾乎一樣")) + "）\n" +
"- Scenario：" + scenario + "\n\n" +
"> 備註：目前只根據 VWAP 一個維度判斷 A/B/C，之後可加上量能、Volume Profile、Options Flow。";

  resultDiv.innerHTML =
    '<table>' +
    '<tr><th>Ticker</th><th>日期</th><th>收盤</th><th>VWAP</th><th>收盤-VWAP%</th><th>Scenario</th></tr>' +
    '<tr>' +
    '<td>' + symbol + '</td>' +
    '<td>' + dateStr + '</td>' +
    '<td>' + closeStr + '</td>' +
    '<td>' + vwapStr + '</td>' +
    '<td>' + pctStr + '%</td>' +
    '<td>' + scenario + '</td>' +
    '</tr>' +
    '</table>' +
    '<p style="margin-top:8px;font-size:12px;color:#666;">最後一根 K 時間（StockData 資料）：' + lastBarTime + '</p>' +
    '<p style="margin-top:12px;font-size:14px;">以下為可直接貼到你的盤後筆記的 Markdown：</p>' +
    '<pre style="white-space:pre-wrap;font-size:12px;border:1px solid #ddd;border-radius:4px;padding:8px;background:#fafafa;">' +
    markdownSnippet +
    '</pre>';
}

// 按鈕事件
document.getElementById("runBtn").addEventListener("click", async function () {
  const symbol = document.getElementById("symbol").value.trim().toUpperCase();
  const dateStr = document.getElementById("date").value.trim();
  const apiKey = document.getElementById("apiKey").value.trim();

  const errorDiv = document.getElementById("error");
  const resultDiv = document.getElementById("result");
  errorDiv.textContent = "";
  resultDiv.style.display = "none";
  clearDebug();

  logDebug("Input params:", { symbol: symbol, dateStr: dateStr });

  if (!symbol || !dateStr || !apiKey) {
    const msg = "請先填寫 Ticker、日期與 StockData API Key。";
    errorDiv.textContent = msg;
    logDebug("Error:", msg);
    return;
  }

  try {
    const raw = await fetchIntradayDataFromStockData(symbol, apiKey, dateStr);
    const dayBars = filterByDate(raw, dateStr);
    const result = calcVWAPAndClose(dayBars);
    const scenarioInfo = decideScenario(result.vwap, result.close);
    renderResult(symbol, dateStr, result.vwap, result.close, scenarioInfo.pct, scenarioInfo.scenario, result.lastBarTime);
  } catch (e) {
    console.error(e);
    errorDiv.textContent = "出錯了：" + e.message;
    logDebug("Caught error:", e.message);
  }
});
