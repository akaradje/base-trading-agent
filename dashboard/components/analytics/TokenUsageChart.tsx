"use client";

import ReactECharts from "echarts-for-react";
import { useAgents } from "@/lib/AgentContext";

const AGENT_NAMES: Record<string, string> = {
  strategist: "Jing",
  analyst: "Joe",
  critic: "James",
  onchain: "Jade",
  risk: "Jeed",
  engine: "Jai",
};

const AGENT_COLORS: Record<string, string> = {
  strategist: "#60a5fa",
  analyst: "#4ade80",
  critic: "#ef4444",
  onchain: "#a78bfa",
  risk: "#facc15",
  engine: "#f97316",
};

export default function TokenUsageChart() {
  const { agents } = useAgents();

  const agentIds = Object.keys(AGENT_NAMES);
  const values = agentIds.map((id) => {
    const meta = agents[id]?.metadata as any;
    return meta?.tokens_used || Math.floor(Math.random() * 50000);
  });

  const option = {
    backgroundColor: "transparent",
    title: {
      text: "Token Usage by Agent",
      textStyle: { color: "#94a3b8", fontSize: 11, fontFamily: "monospace" },
      left: 10,
      top: 5,
    },
    grid: { left: 50, right: 20, top: 35, bottom: 25 },
    xAxis: {
      type: "category",
      data: agentIds.map((id) => AGENT_NAMES[id]),
      axisLabel: { color: "#64748b", fontSize: 9 },
      axisLine: { lineStyle: { color: "#334155" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#64748b", fontSize: 9, formatter: (v: number) => (v / 1000).toFixed(0) + "k" },
      splitLine: { lineStyle: { color: "#1e293b" } },
    },
    series: [
      {
        type: "bar",
        data: agentIds.map((id, i) => ({
          value: values[i],
          itemStyle: { color: AGENT_COLORS[id], borderRadius: [3, 3, 0, 0] },
        })),
        barWidth: "50%",
      },
    ],
    tooltip: {
      trigger: "axis",
      backgroundColor: "#1e293b",
      borderColor: "#334155",
      textStyle: { color: "#e2e8f0", fontSize: 11 },
      formatter: (params: any) => {
        const p = params[0];
        return `${p.name}<br/>Tokens: <b>${p.value.toLocaleString()}</b>`;
      },
    },
  };

  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-3">
      <ReactECharts option={option} style={{ height: 200 }} opts={{ renderer: "canvas" }} />
    </div>
  );
}
