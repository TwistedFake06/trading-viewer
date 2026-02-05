// Wait for DOM and library to be ready
window.addEventListener("DOMContentLoaded", function () {
  // 取得 URL 參數
  const params = new URLSearchParams(window.location.search);
  const symbol = params.get("symbol");
  const date = params.get("date");

  const titleEl = document.getElementById("title");
  const subtitleEl = document.getElementById("subtitle");
  const errorEl = document.getElementById("error-msg");

  if (!symbol || !date) {
    showError("Missing symbol or date parameters.");
  } else {
    titleEl.textContent = `${symbol}`;
    subtitleEl.textContent = `Intraday Data: ${date}`;
    initChart();
  }

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.style.display = "block";
  }

  async function loadData() {
    try {
      const path = `data/intraday/intraday_${symbol}_${date}.json`;
      const resp = await fetch(path);
      if (!resp.ok) throw new Error(`Chart data not found: ${path}`);
      return await resp.json();
    } catch (e) {
      showError(e.message);
      return null;
    }
  }

  async function initChart() {
    const rawData = await loadData();
    if (!rawData || rawData.length === 0) return;

    const container = document.getElementById("chart-container");

    // 確保 LightweightCharts 已載入
    if (typeof LightweightCharts === "undefined") {
      showError("LightweightCharts library failed to load.");
      return;
    }

    // 建立圖表實例
    const chart = LightweightCharts.createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: {
        background: { color: "#1a1a1a" },
        textColor: "#d1d4dc",
      },
      grid: {
        vertLines: { color: "#2B2B43" },
        horzLines: { color: "#2B2B43" },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: "#2B2B43",
      },
    });

    // 1. Candlestick Series
    const candleSeries = chart.addCandlestickSeries({
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderVisible: false,
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
    });

    candleSeries.setData(
      rawData.map((d) => ({
        time: d.time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      })),
    );

    // 2. VWAP Line Series
    const vwapSeries = chart.addLineSeries({
      color: "#ff9800",
      lineWidth: 2,
      title: "VWAP",
    });

    vwapSeries.setData(
      rawData.map((d) => ({
        time: d.time,
        value: d.vwap,
      })),
    );

    // 3. Volume Histogram (Overlay)
    const volumeSeries = chart.addHistogramSeries({
      color: "#26a69a",
      priceFormat: { type: "volume" },
      priceScaleId: "", // 設為空字串，讓它疊加在主圖底部
    });

    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 }, // 限制高度在底部 20%
    });

    volumeSeries.setData(
      rawData.map((d) => ({
        time: d.time,
        value: d.volume,
        color:
          d.close >= d.open
            ? "rgba(38, 166, 154, 0.5)"
            : "rgba(239, 83, 80, 0.5)",
      })),
    );

    // 自適應視窗大小
    window.addEventListener("resize", () => {
      chart.resize(container.clientWidth, container.clientHeight);
    });

    chart.timeScale().fitContent();
  }
});
