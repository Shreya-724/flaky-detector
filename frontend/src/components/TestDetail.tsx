import { splitName, paths, STATUS_LABEL, STATUS_TEXT, type RecentRun, type TestDetailResponse } from "../api";
import { useFetch } from "../hooks";
import RunChart from "./RunChart";

function RunStrip({ runs }: { runs: RecentRun[] }) {
  // The API returns newest first; read the strip left (old) to right (new).
  const ordered = [...runs].reverse();
  return (
    <div className="flex flex-wrap gap-px" role="img" aria-label={`Outcome of the last ${runs.length} runs`}>
      {ordered.map((r, i) => (
        <span
          key={`${r.executed_at}-${i}`}
          title={`${r.commit} on ${r.branch}, attempt ${r.attempt}, ${r.outcome}, ${r.duration_ms ?? "?"}ms`}
          className={`h-3 w-3 ${r.outcome === "passed" ? "bg-pass" : "bg-flaky"} ${
            r.attempt > 1 ? "ring-1 ring-inset ring-neutral-200" : ""
          }`}
        />
      ))}
    </div>
  );
}

export default function TestDetail({ testId }: { testId: number | null }) {
  const { data, error, loading } = useFetch<TestDetailResponse>(testId === null ? null : paths.test(testId), true);

  if (testId === null) return <section className="p-3 text-neutral-500">Select a test to see its history.</section>;
  if (error) return <section className="p-3 text-flaky">Could not load this test: {error}</section>;
  if (!data) return <section className="p-3 text-neutral-500">loading</section>;

  const t = data.test;
  const [mod, fn] = splitName(t.name);
  const noData = t.status === "insufficient_data";
  const metrics: [string, string][] = [
    ["score", t.flakiness_score === null ? "–" : t.flakiness_score.toFixed(1)],
    ["fail", noData ? "–" : `${(t.failure_rate * 100).toFixed(1)}%`],
    ["flip", noData ? "–" : `${(t.flip_rate * 100).toFixed(1)}%`],
    ["conflicts", String(t.conflict_commits)],
    ["runs", String(t.executions)],
  ];

  return (
    <section className={`min-w-0 bg-black transition-opacity motion-reduce:transition-none ${loading ? "opacity-60" : ""}`}>
      <div className="flex items-baseline justify-between gap-3 border-b border-neutral-800 bg-panel px-3 py-2">
        <h2 className="min-w-0 truncate font-normal" title={t.name}>
          <span className="text-neutral-600">{mod && `${mod}::`}</span>
          <span className="text-neutral-100">{fn}</span>
        </h2>
        <span className={`shrink-0 ${STATUS_TEXT[t.status]}`}>{STATUS_LABEL[t.status]}</span>
      </div>

      <dl className="grid grid-cols-5 divide-x divide-neutral-800 border-b border-neutral-800">
        {metrics.map(([k, v]) => (
          <div key={k} className="p-2">
            <dt className="text-neutral-500">{k}</dt>
            <dd className="text-sm tabular-nums">{v}</dd>
          </div>
        ))}
      </dl>

      <div className="border-b border-neutral-800 px-3 pt-2 pb-1 text-neutral-500">Passed and failed runs per day</div>
      <RunChart daily={data.daily} />

      <div className="border-y border-neutral-800 px-3 py-2">
        <div className="mb-1.5 flex items-center justify-between text-neutral-500">
          <span>Last {data.recent.length} runs, oldest to newest</span>
          <span className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 bg-pass" /> pass
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 bg-flaky" /> fail
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 bg-neutral-700 ring-1 ring-inset ring-neutral-200" /> re-run
            </span>
          </span>
        </div>
        <RunStrip runs={data.recent} />
      </div>

      {data.errors.length > 0 && (
        <div className="px-3 py-2">
          <div className="mb-1 text-neutral-500">Most common failures for this test</div>
          <ul>
            {data.errors.map((e) => (
              <li key={e.group_id} className="flex gap-3 py-0.5">
                <span className="w-10 shrink-0 text-right tabular-nums text-flaky">{e.count}×</span>
                <span className="truncate text-neutral-400" title={e.message}>
                  {e.message}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}