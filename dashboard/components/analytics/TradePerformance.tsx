"use client";

import ReactECharts from "echarts-for-react";
import { useTrades } from "@/lib/AgentContext";

export default function TradePerformance() {
  const trades = useTrades();

  // Build cumulative P&L from trades
  const sorted = [...trades].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime());
  let cumPnl = 0;
  const data: [string, number][] = sorted.map((t) => {
    const pnl = t.side === "buy" ? t.price * t.qty * 0.001 : -t.price * t.qty * 0.001;
    cumPnl += pnl;
    return [new Date(t.ts).toLocaleDateString(), Math.round(cumPnl * 100) / 100];
  });

  // If no trades, show placeholder
  if (data.length === 0) {
    data.push([new Date().toLocaleDateString(), 0]);
  }

  const option = {
    backgroundColor: "transparent",
    title: {
      text: "Cumulative P&L",
      textStyle: { color: "#94a3b8", fontSize: 11, fontFamily: "monospace" },
      left: 10,
      top: 5,
    },
    grid: { left: 50, right: 20, top: 35, bottom: 25 },
    xAxis: {
      type: "category",
      data: data.map((d) => d[0]),
      axisLabel: { color: "#64748b", fontSize: 9 },
      axisLine: { lineStyle: { color: "#334155" } },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: "#64748b",
        fontSize: 9,
        formatter: (v: number) => "$" + v.toFixed(0),
      },
      splitLine: { lineStyle: { color: "#1e293b" } },
    },
    series: [
      {
        type: "line",
        data: data.map((d) => d[1]),
        smooth: true,
        lineStyle: { color: "#4ade80", width: 2 },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(74, 222, 128, 0.3)" },
              { offset: 1, color: "rgba(74, 222, 128, 0.02)" },
            ],
          },
        },
        symbol: "circle",
        symbolSize: 4,
        itemStyle: { color: "#4ade80" },
      },
    ],
    tooltip: {
      trigger: "axis",
      backgroundColor: "#1e293b",
      borderColor: "#334155",
      textStyle: { color: "#e2e8f0", fontSize: 11 },
      formatter: (params: any) => {
        const p = params[0];
        return `${p.axisValue}<br/>P&L: <b>$${p.value.toFixed(2)}</b>`;
      },
    },
  };

  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-3">
      <ReactECharts option={option} style={{ height: 200 }} opts={{ renderer: "canvas" }} />
    </div>
  );
}
