import { paths, type Page, type Stats, type TestRow } from "../api";
import ErrorsPreview from "../components/ErrorsPreview";
import StatHeader from "../components/StatHeader";
import TopTestsPreview from "../components/TopTestsPreview";
import { useFetch } from "../hooks";
import { useLayoutData } from "../layoutContext";

export default function OverviewPage() {
  const { stats } = useLayoutData();
  // Fetched separately (not reused from Tests page) so this page works standalone.
  const tests = useFetch<Page<TestRow>>(paths.tests({ statuses: [], search: "", page: 1 }));

  return (
    <div className="flex flex-1 flex-col">
      <StatHeader stats={stats as Stats | undefined} />
      <div className="grid flex-1 grid-cols-1 divide-y divide-neutral-800 xl:grid-cols-2 xl:divide-x xl:divide-y-0">
        <TopTestsPreview tests={tests.data?.results} error={tests.error} />
        <ErrorsPreview />
      </div>
    </div>
  );
}