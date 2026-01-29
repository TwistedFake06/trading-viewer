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
  document.getElementById("debug").textContent = "";
}

// 從 data/vwap_YYYY-MM-DD.json 讀資料（多檔）
async function loadVwapJson(dateStr) {
  const path = "data/vwap_" + dateStr + ".json";
  logDebug("Fetch JSON:", path);

  const resp = await fetch(path);
  if (!resp.ok) {
    throw new Error("讀取失敗：" + resp.status + " " + resp.statusText);
  }
  const json = await resp.json();
  logDebug("JSON loaded, count:", json.length);
  if (json.length > 0) {
    logDebug("First row sample:", json[0]);
  }
  return json;
}

// 根據 close_vwap_pct 決定 Scenario
function decideScenario(pct) {
  if (pct > 0.5) return "A（偏多：收盤在 VWAP 明顯上方）";
  if (pct < -0.5) return "B（偏空：收盤在 VWAP 明顯下方）";
  return "C（中性：收盤貼近 VWAP）";
}

// 顯示結果表格＋ Markdown 區塊
function renderResult(dateStr, rows) {
  const resultDiv = document.getElementById("result");
  resultDiv.style.display = "block";

  // 依 symbol 排序，顯示全部（不再 slice(0,3)）
  const sorted = rows.slice().sort((a, b) => a.symbol.localeCompare(b.symbol));

  // 建表格
  let tableHtml = "<table>";
  tableHtml += "<tr><th>Ticker</th><th>日期</th><th>收盤</th><th>VWAP</th><th>收盤-VWAP%</th><th>Scenario</th></tr>";

  sorted.forEach(row => {
    const pct = row.close_vwap_pct;
    const scenario = decideScenario(pct);
    tableHtml +=
      "<tr>" +
      "<td>" + row.symbol + "</td>" +
      "<td>" + row.date + "</td>" +
      "<td>" + row.close.toFixed(4) + "</td>" +
      "<td>" + row.vwap.toFixed(4) + "</td>" +
      "<td>" + pct.toFixed(2) + "%</td>" +
      "<td>" + scenario + "</td>" +
      "</tr>";
  });

  tableHtml += "</table>";

  // 建 Markdown 片段
  let md = "### VWAP 盤後摘要（" + dateStr + "）\n\n";
  sorted.forEach(row => {
    const pct = row.close_vwap_pct;
    const scenario = decideScenario(pct);
    md +=
`#### ${row.symbol}

- 收盤價：\`${row.close.toFixed(4)}\`
- 全日 VWAP：\`${row.vwap.toFixed(4)}\`
- 收盤相對 VWAP：\`${pct.toFixed(2)}%\`（${pct > 0 ? "在上方" : (pct < 0 ? "在下方" : "幾乎一樣")}）
- Scenario：\`${scenario}\`

`;
  });

  resultDiv.innerHTML =
    tableHtml +
    '<p style="margin-top:12px;font-size:14px;">以下為可直接貼到盤後筆記的 Markdown：</p>' +
    '<pre style="white-space:pre-wrap;font-size:12px;border:1px solid #ddd;border-radius:4px;padding:8px;background:#fafafa;">' +
    md +
    "</pre>";
}

// 按鈕事件
document.getElementById("runBtn").addEventListener("click", async function () {
  const dateStr = document.getElementById("date").value.trim();
  const errorDiv = document.getElementById("error");
  const resultDiv = document.getElementById("result");
  errorDiv.textContent = "";
  resultDiv.style.display = "none";
  clearDebug();

  if (!dateStr) {
    const msg = "請先填寫日期（YYYY-MM-DD）。";
    errorDiv.textContent = msg;
    logDebug("Error:", msg);
    return;
  }

  try {
    const rows = await loadVwapJson(dateStr);
    if (!rows || rows.length === 0) {
      throw new Error("JSON 檔沒有任何資料。");
    }
    renderResult(dateStr, rows);
  } catch (e) {
    console.error(e);
    errorDiv.textContent = "出錯了：" + e.message;
    logDebug("Caught error:", e.message);
  }
});
