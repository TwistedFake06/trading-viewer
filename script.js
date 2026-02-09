// script.js - VWAP & Premarket Dashboard 前端邏輯

// 表格排序輔助函數
function addTableSorting(tableId) {
  const table = document.getElementById(tableId);
  if (!table) return;

  const headers = table.querySelectorAll("th");
  headers.forEach((header, index) => {
    header.style.cursor = "pointer";
    header.addEventListener("click", () => {
      const rows = Array.from(table.tBodies[0].rows);
      const isAsc = !header.classList.contains("asc");

      headers.forEach((h) => h.classList.remove("asc", "desc"));
      header.classList.add(isAsc ? "asc" : "desc");

      rows.sort((a, b) => {
        let aVal = a.cells[index].textContent.trim();
        let bVal = b.cells[index].textContent.trim();

        // 嘗試轉數字排序
        const aNum = parseFloat(aVal);
        const bNum = parseFloat(bVal);
        if (!isNaN(aNum) && !isNaN(bNum)) {
          return isAsc ? aNum - bNum : bNum - aNum;
        }

        // 字串排序
        return isAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      });

      rows.forEach((row) => table.tBodies[0].appendChild(row));
    });
  });
}

// 決定 VWAP 情境顯示文字
function decideScenario(pct) {
  if (pct > 0.5) return "A (偏多)";
  if (pct < -0.5) return "B (偏空)";
  return "C (中性)";
}

// 渲染 VWAP 結果表格
function renderVwapResult(dateStr, rows) {
  const resultDiv = document.getElementById("result");
  if (!resultDiv) {
    console.error("找不到 #result 元素");
    return;
  }

  const sorted = rows.slice().sort((a, b) => a.symbol.localeCompare(b.symbol));

  let html = `<h3>📉 盤後 VWAP 分析 (${dateStr})</h3>`;
  html += `<table id="vwapTable"><thead><tr>`;
  html += `<th>Ticker</th><th>收盤</th><th>VWAP</th><th>差距%</th><th>狀態</th></tr></thead><tbody>`;

  sorted.forEach((row) => {
    const pct = row.close_vwap_pct;
    const styleClass = pct > 0 ? "trend-up" : pct < 0 ? "trend-down" : "";
    const link = `<a href="chart.html?symbol=${row.symbol}&date=${row.date}" target="_blank" style="color:#007bff; text-decoration:none; font-weight:bold;">${row.symbol}</a>`;

    html += `<tr>
      <td>${link}</td>
      <td>${row.close.toFixed(2)}</td>
      <td>${row.vwap.toFixed(2)}</td>
      <td class="${styleClass}">${pct.toFixed(2)}%</td>
      <td>${decideScenario(pct)}</td>
    </tr>`;
  });

  html += `</tbody></table>`;

  resultDiv.innerHTML = html;
  resultDiv.style.display = "block";

  // 啟用排序
  addTableSorting("vwapTable");
}

// 渲染盤前掃描結果表格
function renderPremarketResult(dateStr, rows) {
  const resultDiv = document.getElementById("result");
  if (!resultDiv) {
    console.error("找不到 #result 元素");
    return;
  }

  const sorted = rows.slice().sort((a, b) => b.total_score - a.total_score);

  let html = `<h3>🚀 盤前掃描 (${dateStr})</h3>`;
  html += `<table id="premarketTable"><thead><tr>`;
  html += `<th>Ticker</th><th>昨勢</th><th>盤前價</th><th>漲跌%</th><th>期權分</th><th>總分</th></tr></thead><tbody>`;

  sorted.forEach((row) => {
    const changeClass =
      row.gap_pct > 0 ? "trend-up" : row.gap_pct < 0 ? "trend-down" : "";
    const scoreClass = row.total_score >= 4 ? "score-high" : "";

    const link = `<a href="chart.html?symbol=${row.symbol}&date=${dateStr}" target="_blank" style="color:#007bff; text-decoration:none; font-weight:bold;">${row.symbol}</a>`;

    html += `<tr>
      <td>${link}</td>
      <td>${row.prev_trend}</td>
      <td>${row.price.toFixed(2)}</td>
      <td class="${changeClass}">${row.gap_pct.toFixed(2)}%</td>
      <td>${row.opt_total_score}</td>
      <td class="${scoreClass}">${row.total_score}</td>
    </tr>`;
  });

  html += `</tbody></table>`;

  resultDiv.innerHTML = html;
  resultDiv.style.display = "block";

  // 啟用排序
  addTableSorting("premarketTable");
}

// 主載入邏輯 - 按鈕點擊事件
document.addEventListener("DOMContentLoaded", function () {
  const runBtn = document.getElementById("runBtn");
  if (!runBtn) {
    console.error("找不到 #runBtn 按鈕");
    return;
  }

  runBtn.addEventListener("click", async function () {
    const dateInput = document.getElementById("date");
    const modeSelect = document.getElementById("modeSelect");
    const errorDiv = document.getElementById("error");
    const resultDiv = document.getElementById("result");

    // 防呆檢查所有必要 DOM 元素
    if (!dateInput || !modeSelect || !errorDiv || !resultDiv) {
      console.error("頁面缺少必要元素，請檢查 index.html");
      if (errorDiv) {
        errorDiv.textContent = "頁面載入錯誤：缺少必要元素，請重新整理頁面";
        errorDiv.style.display = "block";
      }
      return;
    }

    const dateStr = dateInput.value.trim();
    const mode = modeSelect.value;

    errorDiv.textContent = "";
    errorDiv.style.display = "none";
    resultDiv.style.display = "none";

    if (!dateStr) {
      errorDiv.textContent = "請選擇日期。";
      errorDiv.style.display = "block";
      return;
    }

    try {
      let rows;

      if (mode === "vwap") {
        const resp = await fetch(`data/vwap_${dateStr}.json`);
        if (!resp.ok) {
          throw new Error(`找不到該日期的 VWAP 資料 (${resp.status})`);
        }
        rows = await resp.json();
        renderVwapResult(dateStr, rows);
      } else {
        // premarket
        const resp = await fetch(`data/premarket_${dateStr}.json`);
        if (!resp.ok) {
          throw new Error(`找不到該日期的盤前資料 (${resp.status})`);
        }
        rows = await resp.json();
        renderPremarketResult(dateStr, rows);
      }
    } catch (e) {
      console.error("資料載入失敗:", e);
      errorDiv.textContent = "載入失敗：" + e.message;
      errorDiv.style.display = "block";
    }
  });

  // 預設填入今日日期
  const today = new Date().toISOString().split("T")[0];
  document.getElementById("date").value = today;
});
