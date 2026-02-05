// -------------------- Debug Helper --------------------
function logDebug(message, obj) {
  const debugEl = document.getElementById("debug");
  const time = new Date().toISOString().split("T")[1].split(".")[0];
  let line = "[" + time + "] " + message;
  if (obj !== undefined) {
    try {
      line += " " + JSON.stringify(obj, null, 2);
    } catch (e) {
      line += " (obj error)";
    }
  }
  debugEl.textContent += line + "\n";
  console.log(line);
}

function clearDebug() {
  document.getElementById("debug").textContent = "";
}

// -------------------- Data Loading --------------------

// 載入 VWAP JSON (盤後數據)
async function loadVwapJson(dateStr) {
  const path = "data/vwap_" + dateStr + ".json";
  logDebug("Fetching VWAP:", path);
  const resp = await fetch(path);
  if (!resp.ok) throw new Error("找不到該日期的 VWAP 資料 (404)");
  return await resp.json();
}

// 載入 Premarket JSON (盤前掃描)
async function loadPremarketJson(dateStr) {
  const path = "data/premarket_" + dateStr + ".json";
  logDebug("Fetching Premarket:", path);
  const resp = await fetch(path);
  if (!resp.ok) throw new Error("找不到該日期的盤前資料 (404)");
  return await resp.json();
}

// -------------------- Rendering Logic --------------------

function decideScenario(pct) {
  if (pct > 0.5) return "A (偏多)";
  if (pct < -0.5) return "B (偏空)";
  return "C (中性)";
}

// 渲染 VWAP 表格
function renderVwapResult(dateStr, rows) {
  const resultDiv = document.getElementById("result");
  const sorted = rows.slice().sort((a, b) => a.symbol.localeCompare(b.symbol));

  let html = `<h3>📉 盤後 VWAP 分析 (${dateStr})</h3>`;
  html +=
    "<table><thead><tr><th>Ticker</th><th>收盤</th><th>VWAP</th><th>差距%</th><th>狀態</th></tr></thead><tbody>";

  sorted.forEach((row) => {
    const pct = row.close_vwap_pct;
    const styleClass = pct > 0 ? "trend-up" : pct < 0 ? "trend-down" : "";

    // 建立連到 intraday.html 的連結，自動載入 intraday JSON
    // 注意：row.date 確保連結到該筆資料實際存在的日期
    const symbolLink = `<a href="intraday.html?symbol=${row.symbol}&date=${row.date}" target="_blank" style="text-decoration:none; color:#007bff; font-weight:bold;">${row.symbol}</a>`;

    html += `<tr>
      <td>${symbolLink}</td>
      <td>${row.close.toFixed(2)}</td>
      <td>${row.vwap.toFixed(2)}</td>
      <td class="${styleClass}">${pct.toFixed(2)}%</td>
      <td>${decideScenario(pct)}</td>
    </tr>`;
  });
  html += "</tbody></table>";

  // Markdown 輸出區塊
  let md = `### VWAP 盤後摘要 (${dateStr})\n\n`;
  sorted.forEach((row) => {
    md += `- **${row.symbol}**: 收 ${row.close} (VWAP ${row.vwap}) | ${row.close_vwap_pct}% (${decideScenario(row.close_vwap_pct)})\n`;
  });

  html += `<p style="font-size:12px;color:#666;">Markdown (可複製):</p>
           <pre style="background:#eee;padding:10px;border-radius:4px;overflow:auto;">${md}</pre>`;

  resultDiv.innerHTML = html;
  resultDiv.style.display = "block";
}

// 渲染 Premarket 表格
function renderPremarketResult(dateStr, rows) {
  const resultDiv = document.getElementById("result");
  // 依總分高低排序
  const sorted = rows.slice().sort((a, b) => b.total_score - a.total_score);

  let html = `<h3>🚀 盤前掃描 (${dateStr})</h3>`;
  html +=
    "<table><thead><tr><th>Ticker</th><th>昨勢</th><th>盤前價</th><th>漲跌%</th><th>期權分</th><th>總分</th></tr></thead><tbody>";

  sorted.forEach((row) => {
    const changeClass =
      row.change_pct > 0 ? "trend-up" : row.change_pct < 0 ? "trend-down" : "";
    const scoreClass = row.total_score >= 4 ? "score-high" : "";

    // 盤前掃描：連結到 intraday 圖表
    // 使用者點進去若有檔就能看到日內圖表
    const symbolLink = `<a href="intraday.html?symbol=${row.symbol}&date=${dateStr}" target="_blank" style="text-decoration:none; color:#007bff; font-weight:bold;">${row.symbol}</a>`;

    html += `<tr>
      <td>${symbolLink}</td>
      <td>${row.prev_trend}</td>
      <td>${row.price.toFixed(2)}</td>
      <td class="${changeClass}">${row.change_pct.toFixed(2)}%</td>
      <td>${row.opt_score}</td>
      <td class="${scoreClass}">${row.total_score}</td>
    </tr>`;
  });
  html += "</tbody></table>";

  // Markdown 輸出區塊 (Top 5)
  let md = `### 盤前重點掃描 (${dateStr})\n\n`;
  sorted.slice(0, 5).forEach((row) => {
    const icon = row.change_pct > 0 ? "📈" : "📉";
    md += `- **${row.symbol}**: ${icon} ${row.change_pct.toFixed(2)}% | Score: ${row.total_score}\n`;
  });

  html += `<p style="font-size:12px;color:#666;">Markdown (Top 5):</p>
           <pre style="background:#eee;padding:10px;border-radius:4px;overflow:auto;">${md}</pre>`;

  resultDiv.innerHTML = html;
  resultDiv.style.display = "block";
}

// -------------------- Event Listeners --------------------

document.getElementById("runBtn").addEventListener("click", async function () {
  const dateStr = document.getElementById("date").value.trim();
  const mode = document.getElementById("modeSelect").value;
  const errorDiv = document.getElementById("error");
  const resultDiv = document.getElementById("result");

  errorDiv.textContent = "";
  resultDiv.style.display = "none";
  clearDebug();

  if (!dateStr) {
    errorDiv.textContent = "請選擇日期。";
    return;
  }

  try {
    if (mode === "vwap") {
      const rows = await loadVwapJson(dateStr);
      renderVwapResult(dateStr, rows);
    } else {
      const rows = await loadPremarketJson(dateStr);
      renderPremarketResult(dateStr, rows);
    }
  } catch (e) {
    console.error(e);
    errorDiv.textContent = "載入失敗：" + e.message;
    logDebug("Error:", e.message);
  }
});

// 初始化：預設填入今天日期
document.getElementById("date").valueAsDate = new Date();
