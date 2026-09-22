import { useState } from "react";
import { API_BASE, PROJECT_SLUG, paths, type ErrorGroupRow, type Page, type Stats, type Status, type TestRow } from "./api";
import ErrorPanel from "./components/ErrorPanel";
import StatHeader from "./components/StatHeader";
import TestDetail from "./components/TestDetail";
import TestTable from "./components/TestTable";
import { useDebounced, useFetch } from "./hooks";

export default function App() {
  const [statuses, setStatuses] = useState<Status[]>([]);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pickedId, setPickedId] = useState<number | null>(null);
  const query = useDebounced(search.trim(), 250);

  const stats = useFetch<Stats>(paths.stats);
  const errors = useFetch<ErrorGroupRow[]>(paths.errors);
  const tests = useFetch<Page<TestRow>>(paths.tests({ statuses, search: query, page }), true);

  // Until the user picks a row, show the top-ranked test.
  const selectedId = pickedId ?? tests.data?.results[0]?.id ?? null;

  return (
    <main className="min-h-screen bg-black font-mono text-xs text-neutral-100">
      <header className="flex items-center justify-between gap-3 border-b border-neutral-800 bg-panel px-3 py-2">
        <h1 className="font-semibold">
          flaky-detector <span className="font-normal text-neutral-500">/ {PROJECT_SLUG}</span>
        </h1>
        <span className="text-neutral-500">
          default branch {stats.data?.project.default_branch ?? "–"}, scoring window {stats.data?.window_days ?? "–"}d
        </span>
      </header>

      {stats.error && (
        <p className="border-b border-neutral-800 bg-panel px-3 py-2 text-flaky">
          Can't load project "{PROJECT_SLUG}" from {API_BASE} ({stats.error}). Start the backend with
          `python manage.py runserver`, then check that the project is marked public in the admin.
        </p>
      )}

      <StatHeader stats={stats.data} />

      <div className="grid grid-cols-1 border-b border-neutral-800 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] lg:divide-x lg:divide-neutral-800">
        <TestTable
          data={tests.data}
          loading={tests.loading}
          error={tests.error}
          counts={stats.data?.tests}
          statuses={statuses}
          onStatuses={(next) => {
            setStatuses(next);
            setPage(1);
          }}
          search={search}
          onSearch={(next) => {
            setSearch(next);
            setPage(1);
          }}
          page={page}
          onPage={setPage}
          selectedId={selectedId}
          onSelect={setPickedId}
        />
        <TestDetail testId={selectedId} />
      </div>

      <ErrorPanel groups={errors.data} error={errors.error} />
    </main>
  );
}