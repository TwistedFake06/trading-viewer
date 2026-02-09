// chart.js - 完整最終版（2026-02-09）：只強制 symbol，date 可選，累加資料模式

window.addEventListener("DOMContentLoaded", function () {
  const params = new URLSearchParams(window.location.search);
  const symbol = params.get("symbol")?.toUpperCase();
  const date = params.get("date");  // date 現在是可選的

  const titleEl = document.getElementById("title");
  const subtitleEl = document.getElementById("subtitle");
  const errorEl = document.getElementById("error-msg");

  if (!symbol) {
    errorEl.textContent = "缺少 symbol 參數（請使用 ?symbol=AMD 格式）";
    errorEl.style.display = "block";
    return;
  }

  titleEl.textContent = symbol;
  subtitleEl.textContent = date 
    ? `Intraday Data: ${date}`
    : "所有歷史 Intraday 資料（最新累加）";

  initChart(symbol);
});

async function initChart(symbol) {
  const container = document.getElementById("chart-container");
  const errorEl = document.getElementById("error-msg");
  const subtitleEl = document.getElementById("subtitle");

  try {
    const path = `data/intraday/intraday_${symbol}.json`;
    console.log("[DEBUG] 嘗試載入資料:", path);

    const resp = await fetch(path);
    if (!resp.ok) {
      throw new Error(`找不到資料檔案：${path} (HTTP ${resp.status})`);
    }

    const rawData = await resp.json();
    if (!Array.isArray(rawData) || rawData.length === 0) {
      throw new Error("資料為空或格式錯誤（非陣列）");
    }

    console.log("[DEBUG] 成功載入資料筆數:", rawData.length);

    if (typeof LightweightCharts === "undefined") {
      throw new Error("LightweightCharts 庫載入失敗，請檢查 CDN 或網路");
    }

    const chart = LightweightCharts.createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: { background: { color: "#111" }, textColor: "#ddd" },
      grid: { vertLines: { color: "#222" }, horzLines: { color: "#222" } },
      rightPriceScale: { borderColor: "#333" },
      timeScale: { borderColor: "#333", timeVisible: true, secondsVisible: false },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#089981",
      downColor: "#F23645",
      borderVisible: false,
      wickUpColor: "#089981",
      wickDownColor: "#F23645",
    });
    candleSeries.setData(rawData.map(d => ({
      time: d.time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    })));

    const vwapSeries = chart.addLineSeries({
      color: "#FF9800",
      lineWidth: 2,
      title: "VWAP",
    });
    vwapSeries.setData(rawData.map(d => ({ time: d.time, value: d.vwap })));

    const volumeSeries = chart.addHistogramSeries({
      color: "#26a69a",
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    volumeSeries.setData(rawData.map(d => ({
      time: d.time,
      value: d.volume,
      color: d.close >= d.open ? "rgba(8,153,129,0.5)" : "rgba(242,54,69,0.5)",
    })));

    // Resize 監聽
    const resizeObserver = new ResizeObserver(() => {
      chart.resize(container.clientWidth, container.clientHeight);
    });
    resizeObserver.observe(container);

    chart.timeScale().fitContent();

    // 顯示最後更新時間
    if (rawData.length > 0) {
      const lastTime = new Date(rawData[rawData.length - 1].time * 1000);
      subtitleEl.textContent += `（最新更新：${lastTime.toLocaleString()}）`;
    }

    console.log("[DEBUG] 圖表初始化完成");

  } catch (e) {
    console.error("圖表初始化失敗:", e);
    errorEl.textContent = e.message;
    errorEl.style.display = "block";
  }
}