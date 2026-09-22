import { paths, type ErrorGroupRow } from "../api";
import ErrorPanel from "../components/ErrorPanel";
import { useFetch } from "../hooks";

export default function ErrorsPage() {
  const { data, error } = useFetch<ErrorGroupRow[]>(paths.errors);
  return (
    <div className="flex flex-1 flex-col">
      <ErrorPanel groups={data} error={error} />
    </div>
  );
}