import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DailyPoint } from "../api";

const PASS = "#10B981";
const FAIL = "#F59E0B";

interface Row {
  date: string;
  label: string;
  passed: number;
  failed: number;
  rate: number;
}

function CodeTooltip({ active, payload }: { active?: boolean; payload?: ReadonlyArray<{ payload?: Row }> }) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  return (
    <div className="border border-neutral-700 bg-black px-2 py-1.5 text-[11px] leading-relaxed whitespace-pre text-neutral-300">
      <div className="text-neutral-600">{`// ${row.date}`}</div>
      <div>
        <span className="text-pass">passed</span>
        {`: ${row.passed}`}
      </div>
      <div>
        <span className="text-flaky">failed</span>
        {`: ${row.failed}`}
      </div>
      <div>
        <span className="text-neutral-500">rate</span>
        {`:   ${row.rate.toFixed(1)}%`}
      </div>
    </div>
  );
}

export default function RunChart({ daily }: { daily: DailyPoint[] }) {
  if (daily.length === 0) return <p className="p-3 text-neutral-500">No runs of this test in the scoring window.</p>;

  const rows: Row[] = daily.map((d) => ({
    date: d.date,
    label: d.date.slice(5),
    passed: d.runs - d.failures,
    failed: d.failures,
    rate: d.runs > 0 ? (d.failures / d.runs) * 100 : 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barCategoryGap={1}>
        <CartesianGrid vertical={false} stroke="#171717" />
        <XAxis
          dataKey="label"
          tick={{ fill: "#737373", fontSize: 10 }}
          tickLine={false}
          axisLine={{ stroke: "#262626" }}
          interval="preserveStartEnd"
          minTickGap={16}
        />
        <YAxis
          allowDecimals={false}
          width={32}
          tick={{ fill: "#737373", fontSize: 10 }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip content={<CodeTooltip />} cursor={{ fill: "rgba(245,158,11,0.08)" }} isAnimationActive={false} />
        <Bar dataKey="passed" stackId="runs" fill={PASS} isAnimationActive={false} />
        <Bar dataKey="failed" stackId="runs" fill={FAIL} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}