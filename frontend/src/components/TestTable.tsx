import {
  PAGE_SIZE,
  splitName,
  STATUS_BAR,
  STATUS_LABEL,
  STATUS_TEXT,
  type Page,
  type Stats,
  type Status,
  type TestRow,
} from "../api";

const FILTERS: Status[] = ["flaky", "suspect", "stable", "insufficient_data"];

interface Props {
  data?: Page<TestRow>;
  loading: boolean;
  error?: string;
  counts?: Stats["tests"];
  statuses: Status[];
  onStatuses: (next: Status[]) => void;
  search: string;
  onSearch: (next: string) => void;
  page: number;
  onPage: (next: number) => void;
  selectedId: number | null;
  onSelect: (id: number) => void;
}

export default function TestTable({
  data,
  loading,
  error,
  counts,
  statuses,
  onStatuses,
  search,
  onSearch,
  page,
  onPage,
  selectedId,
  onSelect,
}: Props) {
  const pages = Math.max(1, Math.ceil((data?.count ?? 0) / PAGE_SIZE));

  function toggle(status: Status) {
    onStatuses(statuses.includes(status) ? statuses.filter((s) => s !== status) : [...statuses, status]);
  }

  return (
    <section className="flex min-w-0 flex-col bg-black">
      <div className="flex flex-wrap items-center gap-2 border-b border-neutral-800 bg-panel p-2">
        <label className="flex min-w-48 flex-1 items-center gap-2 border border-neutral-800 bg-black px-2 py-1 shadow-[inset_0_1px_3px_rgba(0,0,0,0.9)] focus-within:border-flaky">
          <span className="text-flaky">/</span>
          <input
            type="text"
            value={search}
            onChange={(e) => onSearch(e.target.value)}
            spellCheck={false}
            placeholder="filter by test name"
            aria-label="Filter tests by name"
            className="w-full bg-transparent text-neutral-100 outline-none placeholder:text-neutral-600"
          />
        </label>
        {FILTERS.map((s) => {
          const on = statuses.includes(s);
          return (
            <button
              key={s}
              type="button"
              aria-pressed={on}
              onClick={() => toggle(s)}
              className={`border px-2 py-1 outline-none focus-visible:border-flaky ${
                on
                  ? "border-flaky text-flaky"
                  : "border-neutral-800 text-neutral-500 hover:border-neutral-600 hover:text-neutral-300"
              }`}
            >
              {STATUS_LABEL[s]}
              {counts && <span className="ml-1.5 text-neutral-600">{counts[s]}</span>}
            </button>
          );
        })}
      </div>

      <div className={`max-h-[26rem] overflow-auto ${loading ? "opacity-60" : ""}`}>
        <table className="w-full border-collapse text-left">
          <thead className="sticky top-0 bg-panel text-neutral-500">
            <tr className="border-b border-neutral-800">
              <th className="w-10 px-3 py-1.5 text-right font-normal">#</th>
              <th className="px-3 py-1.5 font-normal">test</th>
              <th className="px-3 py-1.5 font-normal">score</th>
              <th className="px-3 py-1.5 text-right font-normal">fail</th>
              <th className="px-3 py-1.5 text-right font-normal">conflicts</th>
              <th className="px-3 py-1.5 text-right font-normal">runs</th>
              <th className="px-3 py-1.5 font-normal">status</th>
            </tr>
          </thead>
          <tbody>
            {error && (
              <tr>
                <td colSpan={7} className="px-3 py-3 text-flaky">
                  Could not load tests: {error}
                </td>
              </tr>
            )}
            {!error && data && data.results.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-3 text-neutral-500">
                  No tests match these filters. Clear the search or toggle a status.
                </td>
              </tr>
            )}
            {!error && !data && (
              <tr>
                <td colSpan={7} className="px-3 py-3 text-neutral-500">
                  loading
                </td>
              </tr>
            )}
            {data?.results.map((t, i) => {
              const [mod, fn] = splitName(t.name);
              const active = t.id === selectedId;
              const score = t.flakiness_score;
              const noData = t.status === "insufficient_data";
              return (
                <tr
                  key={t.id}
                  tabIndex={0}
                  aria-selected={active}
                  onClick={() => onSelect(t.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelect(t.id);
                    }
                  }}
                  className={`cursor-pointer border-b border-neutral-900 outline-none hover:bg-panel-2 focus-visible:bg-panel-2 ${
                    active ? "bg-panel-2 shadow-[inset_2px_0_0_#F59E0B]" : ""
                  }`}
                >
                  <td className="px-3 py-1.5 text-right tabular-nums text-neutral-600">
                    {(page - 1) * PAGE_SIZE + i + 1}
                  </td>
                  <td className="w-full max-w-0 truncate px-3 py-1.5" title={t.name}>
                    <span className="text-neutral-600">{mod && `${mod}::`}</span>
                    <span className="text-neutral-100">{fn}</span>
                  </td>
                  <td className="px-3 py-1.5">
                    <div className="flex items-center gap-2">
                      <div
                        className="relative h-1.5 w-24 shrink-0 bg-neutral-900"
                        role="meter"
                        aria-label="Flakiness score"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={score ?? undefined}
                      >
                        {score !== null && (
                          <div
                            className={`absolute inset-y-0 left-0 ${STATUS_BAR[t.status]}`}
                            style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
                          />
                        )}
                        <span className="absolute inset-y-0 left-[20%] w-px bg-neutral-600" />
                        <span className="absolute inset-y-0 left-[50%] w-px bg-neutral-600" />
                      </div>
                      <span className="w-9 text-right tabular-nums">{score === null ? "–" : score.toFixed(1)}</span>
                    </div>
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums text-neutral-400">
                    {noData ? "–" : `${(t.failure_rate * 100).toFixed(1)}%`}
                  </td>
                  <td
                    className={`px-3 py-1.5 text-right tabular-nums ${
                      t.conflict_commits > 0 ? "text-flaky" : "text-neutral-600"
                    }`}
                  >
                    {t.conflict_commits}
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums text-neutral-400">{t.executions}</td>
                  <td className={`px-3 py-1.5 ${STATUS_TEXT[t.status]}`}>{STATUS_LABEL[t.status]}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between border-t border-neutral-800 bg-panel px-3 py-1.5 text-neutral-500">
        <span>{data ? `${data.count} tests` : "–"}</span>
        <span className="flex items-center gap-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => onPage(page - 1)}
            className="border border-neutral-800 px-2 py-0.5 outline-none focus-visible:border-flaky enabled:hover:border-flaky enabled:hover:text-flaky disabled:opacity-30"
          >
            prev
          </button>
          <span className="tabular-nums">
            {page} / {pages}
          </span>
          <button
            type="button"
            disabled={page >= pages}
            onClick={() => onPage(page + 1)}
            className="border border-neutral-800 px-2 py-0.5 outline-none focus-visible:border-flaky enabled:hover:border-flaky enabled:hover:text-flaky disabled:opacity-30"
          >
            next
          </button>
        </span>
      </div>
    </section>
  );
}