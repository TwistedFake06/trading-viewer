// script.js - 完整版（包含觸發 GitHub Actions 功能）

// 表格排序功能
function addTableSorting(tableId) {
  const table = document.getElementById(tableId);
  if (!table) return;

  const headers = table.querySelectorAll("th");
  headers.forEach((header, index) => {
    header.addEventListener("click", () => {
      const rows = Array.from(table.tBodies[0].rows);
      const isAsc = !header.classList.contains("asc");

      headers.forEach((h) => h.classList.remove("asc", "desc"));
      header.classList.add(isAsc ? "asc" : "desc");

      rows.sort((a, b) => {
        let aVal = a.cells[index].textContent.trim();
        let bVal = b.cells[index].textContent.trim();

        const aNum = parseFloat(aVal);
        const bNum = parseFloat(bVal);
        if (!isNaN(aNum) && !isNaN(bNum)) {
          return isAsc ? aNum - bNum : bNum - aNum;
        }

        return isAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      });

      rows.forEach((row) => table.tBodies[0].appendChild(row));
    });
  });
}

// VWAP 狀態判斷
function decideScenario(pct) {
  if (pct > 0.5) return "A (偏多)";
  if (pct < -0.5) return "B (偏空)";
  return "C (中性)";
}

// 渲染 VWAP 表格
function renderVwapResult(dateStr, rows) {
  const resultDiv = document.getElementById("result");
  if (!resultDiv) return console.error("Missing #result");

  let html = `<h3>📉 盤後 VWAP 分析 (${dateStr})</h3>`;
  html += `<table id="vwapTable"><thead><tr><th>Ticker</th><th>收盤</th><th>VWAP</th><th>差距%</th><th>狀態</th></tr></thead><tbody>`;

  rows.forEach((row) => {
    const pct = Number(row.close_vwap_pct || 0);
    const cls = pct > 0 ? "trend-up" : pct < 0 ? "trend-down" : "";
    const link = `<a href="chart.html?symbol=${row.symbol}&date=${row.date || dateStr}" target="_blank">${row.symbol}</a>`;

    html += `<tr>
      <td>${link}</td>
      <td>${Number(row.close || 0).toFixed(2)}</td>
      <td>${Number(row.vwap || 0).toFixed(2)}</td>
      <td class="${cls}">${pct.toFixed(2)}%</td>
      <td>${decideScenario(pct)}</td>
    </tr>`;
  });

  html += `</tbody></table>`;
  resultDiv.innerHTML = html;
  resultDiv.style.display = "block";
  addTableSorting("vwapTable");
}

// 渲染盤前掃描表格
function renderPremarketResult(dateStr, rows) {
  const resultDiv = document.getElementById("result");
  if (!resultDiv) return console.error("Missing #result");

  let html = `<h3>🚀 盤前掃描 (${dateStr})</h3>`;
  html += `<table id="premarketTable"><thead><tr><th>Ticker</th><th>昨勢</th><th>盤前價</th><th>漲跌%</th><th>期權分</th><th>總分</th></tr></thead><tbody>`;

  rows.forEach((row) => {
    const pct = Number(row.gap_pct || 0);
    const changeCls = pct > 0 ? "trend-up" : pct < 0 ? "trend-down" : "";
    const scoreCls = Number(row.total_score || 0) >= 4 ? "score-high" : "";

    const link = `<a href="chart.html?symbol=${row.symbol}&date=${dateStr}" target="_blank">${row.symbol}</a>`;

    html += `<tr>
      <td>${link}</td>
      <td>${row.prev_trend || "N/A"}</td>
      <td>${Number(row.price || 0).toFixed(2)}</td>
      <td class="${changeCls}">${pct.toFixed(2)}%</td>
      <td>${row.opt_total_score || 0}</td>
      <td class="${scoreCls}">${row.total_score || 0}</td>
    </tr>`;
  });

  html += `</tbody></table>`;
  resultDiv.innerHTML = html;
  resultDiv.style.display = "block";
  addTableSorting("premarketTable");
}

// 主載入邏輯
document.addEventListener("DOMContentLoaded", () => {
  const runBtn = document.getElementById("runBtn");
  if (!runBtn) return console.error("Missing #runBtn");

  runBtn.addEventListener("click", async () => {
    const dateEl = document.getElementById("date");
    const modeEl = document.getElementById("modeSelect");
    const errorEl = document.getElementById("error");
    const resultEl = document.getElementById("result");

    if (!dateEl || !modeEl || !errorEl || !resultEl) {
      console.error("Missing required DOM elements");
      if (errorEl) errorEl.textContent = "頁面結構錯誤，請檢查 HTML";
      return;
    }

    const dateStr = dateEl.value.trim();
    const mode = modeEl.value;

    errorEl.textContent = "";
    errorEl.style.display = "none";
    resultEl.style.display = "none";

    if (!dateStr) {
      errorEl.textContent = "請選擇日期";
      errorEl.style.display = "block";
      return;
    }

    try {
      const url =
        mode === "vwap"
          ? `data/vwap_${dateStr}.json`
          : `data/premarket_${dateStr}.json`;

      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`找不到資料 (${resp.status}) - ${url}`);

      const data = await resp.json();

      if (mode === "vwap") {
        renderVwapResult(dateStr, data);
      } else {
        renderPremarketResult(dateStr, data);
      }
    } catch (err) {
      console.error("載入失敗", err);
      errorEl.textContent = "載入失敗：" + err.message;
      errorEl.style.display = "block";
    }
  });

  // 預設今天日期
  document.getElementById("date").value = new Date()
    .toISOString()
    .split("T")[0];

  // 新增：觸發 GitHub Actions 抓取指定日期
  const triggerBtn = document.getElementById("triggerActionBtn");
  if (triggerBtn) {
    triggerBtn.addEventListener("click", () => {
      const dateEl = document.getElementById("triggerDate");
      const feedback = document.getElementById("triggerFeedback");

      if (!dateEl.value) {
        feedback.textContent = "請先選擇日期";
        feedback.style.color = "#dc3545";
        setTimeout(() => (feedback.textContent = ""), 3000);
        return;
      }

      const date = dateEl.value; // YYYY-MM-DD
      const repo = "TwistedFake06/trading-viewer"; // 你的 repo 名稱
      const workflow = "vwap_yf.yml"; // workflow 檔名

      // 產生帶有 custom_date 參數的 Actions 頁面連結
      const url = `https://github.com/${repo}/actions/workflows/${workflow}?query=workflow%3A${workflow}+custom_date%3A${date}`;

      feedback.textContent = "已開啟 GitHub 頁面，請點 Run workflow 開始抓取";
      feedback.style.color = "#28a745";

      // 開新分頁
      window.open(url, "_blank");

      setTimeout(() => (feedback.textContent = ""), 8000);
    });
  }
});
