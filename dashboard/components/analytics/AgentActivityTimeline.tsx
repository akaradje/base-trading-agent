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

const STATUS_COLORS: Record<string, string> = {
  working: "#4ade80",
  thinking: "#facc15",
  error: "#ef4444",
  idle: "#64748b",
  celebrate: "#a78bfa",
};

export default function AgentActivityTimeline() {
  const { agents } = useAgents();

  const agentIds = Object.keys(AGENT_NAMES);
  const statusValues = agentIds.map((id) => agents[id]?.status || "idle");

  const option = {
    backgroundColor: "transparent",
    title: {
      text: "Agent Status Overview",
      textStyle: { color: "#94a3b8", fontSize: 11, fontFamily: "monospace" },
      left: 10,
      top: 5,
    },
    grid: { left: 60, right: 20, top: 35, bottom: 10 },
    xAxis: {
      type: "value",
      max: 1,
      show: false,
    },
    yAxis: {
      type: "category",
      data: agentIds.map((id) => AGENT_NAMES[id]),
      axisLabel: { color: "#94a3b8", fontSize: 9 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: "bar",
        data: agentIds.map((id, i) => ({
          value: 1,
          itemStyle: {
            color: STATUS_COLORS[statusValues[i]] || "#64748b",
            borderRadius: [0, 4, 4, 0],
          },
        })),
        barWidth: "60%",
        label: {
          show: true,
          position: "right",
          formatter: (params: any) => statusValues[params.dataIndex],
          color: "#94a3b8",
          fontSize: 9,
        },
      },
    ],
    tooltip: {
      trigger: "axis",
      backgroundColor: "#1e293b",
      borderColor: "#334155",
      textStyle: { color: "#e2e8f0", fontSize: 11 },
      formatter: (params: any) => {
        const p = params[0];
        return `${p.name}: <b>${statusValues[p.dataIndex]}</b>`;
      },
    },
  };

  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-3">
      <ReactECharts option={option} style={{ height: 200 }} opts={{ renderer: "canvas" }} />
    </div>
  );
}
