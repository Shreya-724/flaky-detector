import { Link } from "react-router-dom";
import { splitName, STATUS_BAR, STATUS_LABEL, STATUS_TEXT, type TestRow } from "../api";

const PREVIEW_COUNT = 6;

export default function TopTestsPreview({ tests, error }: { tests?: TestRow[]; error?: string }) {
  return (
    <section className="flex min-w-0 flex-col">
      <div className="flex items-center justify-between border-b border-neutral-800 bg-panel px-3 py-1.5 text-neutral-500">
        <h2 className="font-normal">Top flaky tests</h2>
        <Link to="/tests" className="text-neutral-400 outline-none hover:text-flaky focus-visible:text-flaky">
          view all tests →
        </Link>
      </div>
      {error && <p className="px-3 py-3 text-flaky">Could not load tests: {error}</p>}
      {!tests && !error && <p className="px-3 py-3 text-neutral-500">loading</p>}
      {tests && tests.length === 0 && <p className="px-3 py-3 text-neutral-500">No tests recorded yet.</p>}
      <ul>
        {tests?.slice(0, PREVIEW_COUNT).map((t) => {
          const [mod, fn] = splitName(t.name);
          const score = t.flakiness_score;
          return (
            <li key={t.id} className="border-b border-neutral-900">
              <Link
                to={`/tests/${t.id}`}
                className="flex items-center gap-3 px-3 py-1.5 outline-none hover:bg-panel-2 focus-visible:bg-panel-2"
              >
                <div className="relative h-1.5 w-16 shrink-0 bg-neutral-900">
                  {score !== null && (
                    <div
                      className={`absolute inset-y-0 left-0 ${STATUS_BAR[t.status]}`}
                      style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
                    />
                  )}
                </div>
                <span className="w-10 shrink-0 text-right tabular-nums">{score === null ? "–" : score.toFixed(1)}</span>
                <span className="min-w-0 flex-1 truncate" title={t.name}>
                  <span className="text-neutral-600">{mod && `${mod}::`}</span>
                  <span className="text-neutral-100">{fn}</span>
                </span>
                <span className={`shrink-0 ${STATUS_TEXT[t.status]}`}>{STATUS_LABEL[t.status]}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}