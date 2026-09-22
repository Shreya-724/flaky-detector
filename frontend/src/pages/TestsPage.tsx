import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { paths, type Page, type Status, type TestRow } from "../api";
import TestDetail from "../components/TestDetail";
import TestTable from "../components/TestTable";
import { useDebounced, useFetch } from "../hooks";
import { useLayoutData } from "../layoutContext";

export default function TestsPage() {
  const { stats } = useLayoutData();
  const navigate = useNavigate();
  const { id } = useParams<{ id?: string }>();

  const [statuses, setStatuses] = useState<Status[]>([]);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const query = useDebounced(search.trim(), 250);

  const tests = useFetch<Page<TestRow>>(paths.tests({ statuses, search: query, page }), true);

  // A URL id (deep link, or a row already clicked) wins; otherwise default to the top-ranked test.
  const urlId = id ? Number(id) : null;
  const selectedId = urlId ?? tests.data?.results[0]?.id ?? null;

  return (
    <div className="grid flex-1 grid-cols-1 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] lg:divide-x lg:divide-neutral-800">
      <TestTable
        data={tests.data}
        loading={tests.loading}
        error={tests.error}
        counts={stats?.tests}
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
        onSelect={(testId) => navigate(`/tests/${testId}`)}
      />
      <TestDetail testId={selectedId} />
    </div>
  );
}