// script.js
document.getElementById("runBtn").addEventListener("click", async function () {
  const dateStr = document.getElementById("date").value.trim();
  const mode = document.getElementById("modeSelect").value;
  const errorDiv = document.getElementById("error");
  const resultDiv = document.getElementById("result");
  errorDiv.textContent = "";
  resultDiv.style.display = "none";
  if (!dateStr) {
    errorDiv.textContent = "請選擇日期。";
    return;
  }
  try {
    let rows;
    if (mode === "vwap") {
      rows = await fetch(`data/vwap_${dateStr}.json`).then((res) => {
        if (!res.ok) throw new Error("404");
        return res.json();
      });
      renderVwapResult(dateStr, rows);
    } else {
      rows = await fetch(`data/premarket_${dateStr}.json`).then((res) => {
        if (!res.ok) throw new Error("404");
        return res.json();
      });
      renderPremarketResult(dateStr, rows);
    }
  } catch (e) {
    errorDiv.textContent = "載入失敗：" + e.message;
  }
});
function renderVwapResult(dateStr, rows) {
  const sorted = rows.slice().sort((a, b) => a.symbol.localeCompare(b.symbol));
  let html = `<h3>📉 VWAP 分析 (${dateStr})</h3><table id="vwapTable"><thead><tr><th>Ticker</th><th>收盤</th><th>VWAP</th><th>差距%</th><th>狀態</th></tr></thead><tbody>`;
  sorted.forEach((row) => {
    const pct = row.close_vwap_pct;
    const styleClass = pct > 0 ? "trend-up" : pct < 0 ? "trend-down" : "";
    const link = `<a href="chart.html?symbol=${row.symbol}&date=${row.date}" target="_blank" style="color:#007bff;">${row.symbol}</a>`;
    html += `<tr><td>${link}</td><td>${row.close.toFixed(2)}</td><td>${row.vwap.toFixed(2)}</td><td class="${styleClass}">${pct.toFixed(2)}%</td><td>${decideScenario(pct)}</td></tr>`;
  });
  html += `</tbody></table>`;
  resultDiv.innerHTML = html;
  resultDiv.style.display = "block";
  addTableSorting("vwapTable");
}
function renderPremarketResult(dateStr, rows) {
  const sorted = rows.slice().sort((a, b) => b.total_score - a.total_score);
  let html = `<h3>🚀 盤前掃描 (${dateStr})</h3><table id="premarketTable"><thead><tr><th>Ticker</th><th>昨勢</th><th>盤前價</th><th>漲跌%</th><th>期權分</th><th>總分</th></tr></thead><tbody>`;
  sorted.forEach((row) => {
    const changeClass =
      row.gap_pct > 0 ? "trend-up" : row.gap_pct < 0 ? "trend-down" : "";
    const scoreClass = row.total_score >= 4 ? "score-high" : "";
    const link = `<a href="chart.html?symbol=${row.symbol}&date=${dateStr}" target="_blank" style="color:#007bff;">${row.symbol}</a>`;
    html += `<tr><td>${link}</td><td>${row.prev_trend}</td><td>${row.price.toFixed(2)}</td><td class="${changeClass}">${row.gap_pct.toFixed(2)}%</td><td>${row.opt_total_score}</td><td class="${scoreClass}">${row.total_score}</td></tr>`;
  });
  html += `</tbody></table>`;
  resultDiv.innerHTML = html;
  resultDiv.style.display = "block";
  addTableSorting("premarketTable");
}
function decideScenario(pct) {
  if (pct > 0.5) return "A (偏多)";
  if (pct < -0.5) return "B (偏空)";
  return "C (中性)";
}
function addTableSorting(tableId) {
  const table = document.getElementById(tableId);
  const headers = table.querySelectorAll("th");
  headers.forEach((header, index) => {
    header.addEventListener("click", () => {
      const rows = Array.from(table.tBodies[0].rows);
      const isAsc = header.classList.toggle("asc");
      header.classList.toggle("desc", !isAsc);
      rows.sort((a, b) => {
        const aVal =
          parseFloat(a.cells[index].textContent) || a.cells[index].textContent;
        const bVal =
          parseFloat(b.cells[index].textContent) || b.cells[index].textContent;
        return isAsc ? (aVal > bVal ? 1 : -1) : aVal < bVal ? 1 : -1;
      });
      rows.forEach((row) => table.tBodies[0].appendChild(row));
    });
  });
}
document.getElementById("date").valueAsDate = new Date();
