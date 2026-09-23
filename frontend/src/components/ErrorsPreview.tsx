import { Link, useParams } from "react-router-dom";
import { paths, type ErrorGroupRow } from "../api";
import { useFetch } from "../hooks";

const PREVIEW_COUNT = 6;

export default function ErrorsPreview() {
  const { slug } = useParams<{ slug: string }>();
  const { data, error } = useFetch<ErrorGroupRow[]>(slug ? paths.errors(slug) : null);

  return (
    <section className="flex min-w-0 flex-col">
      <div className="flex items-center justify-between border-b border-neutral-800 bg-panel px-3 py-1.5 text-neutral-500">
        <h2 className="font-normal">Most common failures</h2>
        <Link to="/errors" className="text-neutral-400 outline-none hover:text-flaky focus-visible:text-flaky">
          view all errors →
        </Link>
      </div>
      {error && <p className="px-3 py-3 text-flaky">Could not load error groups: {error}</p>}
      {!data && !error && <p className="px-3 py-3 text-neutral-500">loading</p>}
      {data && data.length === 0 && <p className="px-3 py-3 text-neutral-500">No failures recorded yet.</p>}
      <ul>
        {data?.slice(0, PREVIEW_COUNT).map((g) => (
          <li key={g.id} className="flex items-center gap-3 border-b border-neutral-900 px-3 py-1.5">
            <span className="w-10 shrink-0 text-right tabular-nums text-flaky">{g.occurrences}×</span>
            <span className="min-w-0 flex-1 truncate text-neutral-300" title={g.message}>
              {g.message}
            </span>
            <span className="shrink-0 text-neutral-600">
              {g.tests_affected} {g.tests_affected === 1 ? "test" : "tests"}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}