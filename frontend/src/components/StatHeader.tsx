import type { ReactNode } from "react";
import type { Stats } from "../api";

function Cell({
  label,
  value,
  unit,
  hot,
  children,
}: {
  label: string;
  value: string;
  unit?: string;
  hot?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="p-3">
      <div className="text-neutral-500">{label}</div>
      <div className="mt-1 flex items-baseline gap-1.5">
        <span className={`text-2xl font-semibold tabular-nums ${hot ? "text-flaky" : "text-neutral-100"}`}>
          {value}
        </span>
        {unit && <span className="text-neutral-500">{unit}</span>}
      </div>
      <div className="mt-1 text-[11px] text-neutral-500">{children}</div>
    </div>
  );
}

function DeltaFlag({ pp }: { pp: number | null | undefined }) {
  if (pp === null || pp === undefined) return <span>no prior 7d window</span>;
  if (Math.abs(pp) < 0.05) return <span>■ 0.0pp vs prev 7d</span>;
  return pp > 0 ? (
    <span className="text-flaky">▲ +{pp.toFixed(1)}pp vs prev 7d</span>
  ) : (
    <span className="text-pass">▼ {pp.toFixed(1)}pp vs prev 7d</span>
  );
}

export default function StatHeader({ stats }: { stats?: Stats }) {
  const t = stats?.tests;
  const dash = "–";
  const flakyShare = t && t.total > 0 ? (t.flaky / t.total) * 100 : 0;
  const rerunRate = stats && stats.runs.total > 0 ? (stats.wasted_runs / stats.runs.total) * 100 : 0;
  const rate = stats?.failure_rate?.last_7d;

  return (
    <section className="grid grid-cols-1 divide-y divide-neutral-800 border-b border-neutral-800 bg-panel md:grid-cols-5 md:divide-x md:divide-y-0">
      <Cell
        label="Flaky tests"
        value={t ? String(t.flaky) : dash}
        unit={t ? `of ${t.total}` : undefined}
        hot={!!t && t.flaky > 0}
      >
        {t ? `${flakyShare.toFixed(1)}% of suite, ${t.suspect} suspect` : "loading"}
      </Cell>
      <Cell
        label="Fail rate, last 7d"
        value={rate === null || rate === undefined ? dash : `${rate.toFixed(1)}%`}
      >
        {stats ? <DeltaFlag pp={stats.failure_rate?.delta_pp} /> : "loading"}
      </Cell>
      <Cell
        label={`Flaky failures, ${stats?.window_days ?? 30}d`}
        value={stats ? String(stats.flaky_failures) : dash}
      >
        {stats ? `${stats.runs.total} runs across ${stats.runs.commits} commits` : "loading"}
      </Cell>
      <Cell
        label="CI time wasted (est.)"
        value={stats ? stats.wasted_ci_minutes.toFixed(1) : dash}
        unit={stats ? "min" : undefined}
      >
        {stats ? `${stats.wasted_runs} runs re-run after a flaky failure` : "loading"}
      </Cell>
      <Cell label="Re-run rate" value={stats ? `${rerunRate.toFixed(1)}%` : dash}>
        {stats ? `${stats.wasted_runs} of ${stats.runs.total} runs` : "loading"}
      </Cell>
    </section>
  );
}