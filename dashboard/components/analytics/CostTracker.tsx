"use client";

import ReactECharts from "echarts-for-react";

// Simulated cost data — in production, this comes from agent_metrics table
const MOCK_COSTS = [
  { date: "Mon", cost: 0.42 },
  { date: "Tue", cost: 0.58 },
  { date: "Wed", cost: 0.35 },
  { date: "Thu", cost: 0.71 },
  { date: "Fri", cost: 0.48 },
  { date: "Sat", cost: 0.22 },
  { date: "Sun", cost: 0.31 },
];

export default function CostTracker() {
  const option = {
    backgroundColor: "transparent",
    title: {
      text: "Daily Cost ($)",
      textStyle: { color: "#94a3b8", fontSize: 11, fontFamily: "monospace" },
      left: 10,
      top: 5,
    },
    grid: { left: 40, right: 20, top: 35, bottom: 25 },
    xAxis: {
      type: "category",
      data: MOCK_COSTS.map((d) => d.date),
      axisLabel: { color: "#64748b", fontSize: 9 },
      axisLine: { lineStyle: { color: "#334155" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#64748b", fontSize: 9, formatter: "${value}" },
      splitLine: { lineStyle: { color: "#1e293b" } },
    },
    series: [
      {
        type: "bar",
        data: MOCK_COSTS.map((d) => ({
          value: d.cost,
          itemStyle: {
            color: d.cost > 0.5 ? "#f97316" : "#4ade80",
            borderRadius: [3, 3, 0, 0],
          },
        })),
        barWidth: "40%",
      },
    ],
    tooltip: {
      trigger: "axis",
      backgroundColor: "#1e293b",
      borderColor: "#334155",
      textStyle: { color: "#e2e8f0", fontSize: 11 },
      formatter: (params: any) => {
        const p = params[0];
        return `${p.axisValue}<br/>Cost: <b>$${p.value.toFixed(2)}</b>`;
      },
    },
  };

  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-3">
      <ReactECharts option={option} style={{ height: 200 }} opts={{ renderer: "canvas" }} />
    </div>
  );
}
