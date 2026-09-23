import { useParams } from "react-router-dom";
import { paths, type ErrorGroupRow } from "../api";
import ErrorPanel from "../components/ErrorPanel";
import { useFetch } from "../hooks";

export default function ErrorsPage() {
  const { slug } = useParams<{ slug: string }>();
  const { data, error } = useFetch<ErrorGroupRow[]>(slug ? paths.errors(slug) : null);
  return (
    <div className="flex flex-1 flex-col">
      <ErrorPanel groups={data} error={error} />
    </div>
  );
}