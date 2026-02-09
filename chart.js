// chart.js - v4.x 相容版

window.addEventListener("DOMContentLoaded", function () {
  const params = new URLSearchParams(window.location.search);
  const symbol = params.get("symbol")?.toUpperCase();
  const date = params.get("date");

  const titleEl = document.getElementById("title");
  const subtitleEl = document.getElementById("subtitle");
  const errorEl = document.getElementById("error-msg");

  if (!symbol || !date) {
    errorEl.textContent = "缺少 symbol 或 date 參數";
    errorEl.style.display = "block";
    return;
  }

  titleEl.textContent = symbol;
  subtitleEl.textContent = `Intraday: ${date}`;

  initChart();
});

async function initChart() {
  const params = new URLSearchParams(window.location.search);
  const symbol = params.get("symbol")?.toUpperCase();
  const date = params.get("date");

  const container = document.getElementById("chart-container");
  const errorEl = document.getElementById("error-msg");

  try {
    const path = `data/intraday/intraday_${symbol}.json`;
    const resp = await fetch(path);
    if (!resp.ok) throw new Error(`資料不存在: ${path} (${resp.status})`);

    const rawData = await resp.json();
    if (rawData.length === 0) throw new Error("JSON 資料為空");

    if (typeof LightweightCharts === "undefined") {
      throw new Error("LightweightCharts library 未載入，請檢查 CDN");
    }

    const chart = LightweightCharts.createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: { background: { color: "#111" }, textColor: "#ddd" },
      grid: { vertLines: { color: "#222" }, horzLines: { color: "#222" } },
      rightPriceScale: { borderColor: "#333" },
      timeScale: {
        borderColor: "#333",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#089981",
      downColor: "#F23645",
      borderVisible: false,
      wickUpColor: "#089981",
      wickDownColor: "#F23645",
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
      color: "#FF9800",
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
          d.close >= d.open ? "rgba(8,153,129,0.5)" : "rgba(242,54,69,0.5)",
      })),
    );

    window.addEventListener("resize", () => {
      chart.resize(container.clientWidth, container.clientHeight);
    });

    chart.timeScale().fitContent();
  } catch (e) {
    console.error(e);
    errorEl.textContent = e.message;
    errorEl.style.display = "block";
  }
}
