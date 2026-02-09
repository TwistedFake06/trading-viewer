// chart.js
window.addEventListener("DOMContentLoaded", function () {
  const params = new URLSearchParams(window.location.search);
  const symbol = params.get("symbol");
  const date = params.get("date");
  const titleEl = document.getElementById("title");
  const subtitleEl = document.getElementById("subtitle");
  const errorEl = document.getElementById("error-msg");
  if (!symbol || !date) {
    errorEl.textContent = "Missing symbol or date.";
    errorEl.style.display = "block";
    return;
  }
  titleEl.textContent = `${symbol}`;
  subtitleEl.textContent = `Intraday: ${date}`;
  initChart();
  async function loadData() {
    try {
      const path = `data/intraday/intraday_${symbol}_${date}.json`;
      const resp = await fetch(path);
      if (!resp.ok) throw new Error(`Data not found: ${path}`);
      return await resp.json();
    } catch (e) {
      errorEl.textContent = e.message;
      errorEl.style.display = "block";
      return null;
    }
  }
  async function initChart() {
    const rawData = await loadData();
    if (!rawData || rawData.length === 0) return;
    const container = document.getElementById("chart-container");
    if (typeof LightweightCharts === "undefined") {
      errorEl.textContent = "Library failed to load.";
      return;
    }
    const chart = LightweightCharts.createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: { background: { color: "#1a1a1a" }, textColor: "#d1d4dc" },
      grid: {
        vertLines: { color: "#2B2B43" },
        horzLines: { color: "#2B2B43" },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 5,
        lockVisibleTimeRangeOnResize: true,
        timeZone: "Asia/Hong_Kong",
      },
      rightPriceScale: {
        borderColor: "#2B2B43",
        autoScale: true,
        scaleMargins: { top: 0.1, bottom: 0.2 },
      },
      handleScroll: {
        mouseWheel: false,
        pressedMouseMove: false,
        horzTouchDrag: false,
        vertTouchDrag: false,
      },
      handleScale: {
        axisPressedMouseMove: false,
        mouseWheel: false,
        pinch: false,
      },
    });
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
    const vwapSeries = chart.addLineSeries({
      color: "#ff9800",
      lineWidth: 2,
      title: "VWAP",
    });
    vwapSeries.setData(rawData.map((d) => ({ time: d.time, value: d.vwap })));
    const volumeSeries = chart.addHistogramSeries({
      color: "#26a69a",
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    volumeSeries
      .priceScale()
      .applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
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
    const resizeObserver = new ResizeObserver(() =>
      chart.resize(container.clientWidth, container.clientHeight),
    );
    resizeObserver.observe(container);
    chart.timeScale().fitContent();
  }
});
