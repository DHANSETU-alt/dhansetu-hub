"use client";

import { Line, LineChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import type { HealthSnapshot } from "@/lib/api";

// One hue per chart (this is magnitude-over-time for a single series, not
// a categorical comparison) -- the existing --local accent, already
// validated by use across the rest of this dashboard, not a new palette.
const CONFIG: ChartConfig = {
  value: { label: "value", color: "var(--local)" },
};

function shortTime(iso: string) {
  const d = new Date(iso.replace(" ", "T"));
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function HealthChart({
  snapshots,
  metric,
  unit,
  domain,
}: {
  snapshots: HealthSnapshot[];
  metric: "cpu_percent" | "ram_percent" | "cpu_temp_c";
  unit: string;
  domain?: [number, number];
}) {
  const data = [...snapshots]
    .reverse()
    .filter((s) => s[metric] !== null && s[metric] !== undefined)
    .map((s) => ({ time: shortTime(s.created_at), value: s[metric] as number }));

  if (data.length === 0) {
    return <div className="text-sm text-[var(--muted-foreground)] py-8 text-center">No data yet — needs more than one snapshot.</div>;
  }

  return (
    <ChartContainer config={CONFIG} className="h-[160px] w-full">
      <LineChart data={data} margin={{ left: 4, right: 4, top: 8, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="3 3" />
        <XAxis dataKey="time" tickLine={false} axisLine={false} tickMargin={8} fontSize={11} stroke="var(--muted-foreground)" />
        <YAxis
          tickLine={false}
          axisLine={false}
          tickMargin={4}
          fontSize={11}
          stroke="var(--muted-foreground)"
          domain={domain ?? ["auto", "auto"]}
          tickFormatter={(v) => `${v}${unit}`}
          width={44}
        />
        <ChartTooltip content={<ChartTooltipContent formatter={(v) => [`${v}${unit}`, ""]} />} />
        <Line dataKey="value" type="monotone" stroke="var(--color-value)" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
      </LineChart>
    </ChartContainer>
  );
}
