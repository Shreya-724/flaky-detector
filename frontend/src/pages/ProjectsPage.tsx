import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { authPaths, type OwnedProject } from "../api";
import { useAuth } from "../auth";

export default function ProjectsPage() {
  const { authFetch } = useAuth();
  const [projects, setProjects] = useState<OwnedProject[] | undefined>();
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    authFetch<OwnedProject[]>(authPaths.myProjects)
      .then(setProjects)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [authFetch]);

  return (
    <div className="min-h-screen bg-black font-mono text-xs text-neutral-100">
      <header className="flex items-center justify-between border-b border-neutral-800 bg-panel px-3 py-2">
        <Link to="/" className="font-semibold outline-none hover:text-flaky focus-visible:text-flaky">
          flaky-detector
        </Link>
        <Link
          to="/projects/new"
          className="border border-flaky/60 bg-flaky/10 px-3 py-1 text-flaky outline-none hover:bg-flaky/20 focus-visible:bg-flaky/20"
        >
          + new project
        </Link>
      </header>

      <div className="p-3">
        <h1 className="mb-2 text-neutral-500">My projects</h1>
        {error && <p className="py-3 text-flaky">Could not load your projects: {error}</p>}
        {!projects && !error && <p className="py-3 text-neutral-500">loading</p>}
        {projects && projects.length === 0 && (
          <p className="py-3 text-neutral-500">
            You don't have any projects yet.{" "}
            <Link to="/projects/new" className="text-neutral-300 underline hover:text-flaky">
              Create your first one →
            </Link>
          </p>
        )}
        <ul>
          {projects?.map((p) => (
            <li key={p.id} className="flex flex-wrap items-center gap-3 border-b border-neutral-900 py-2">
              <span className="min-w-0 flex-1 truncate text-neutral-100">{p.name}</span>
              <span className="text-neutral-600">{p.slug}</span>
              <span className={p.is_public ? "text-pass" : "text-neutral-600"}>
                {p.is_public ? "public" : "private"}
              </span>
              <Link
                to={`/p/${p.slug}`}
                className="border border-neutral-800 px-2 py-1 text-neutral-300 outline-none hover:border-flaky hover:text-flaky focus-visible:border-flaky"
              >
                view dashboard
              </Link>
              <Link
                to={`/projects/${p.slug}/settings`}
                className="border border-neutral-800 px-2 py-1 text-neutral-300 outline-none hover:border-flaky hover:text-flaky focus-visible:border-flaky"
              >
                settings
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}