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
    throw new Error("StockDa
