import { Outlet } from "react-router-dom";
import { API_BASE, paths, PROJECT_SLUG, type Stats } from "./api";
import Sidebar from "./components/Sidebar";
import { useFetch } from "./hooks";
import { LayoutDataContext } from "./layoutContext";

export default function Layout() {
  const stats = useFetch<Stats>(paths.stats);

  return (
    <div className="flex min-h-screen flex-col bg-black font-mono text-xs text-neutral-100">
      <header className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-neutral-800 bg-panel px-3 py-2">
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

      <div className="flex flex-1 flex-col lg:flex-row">
        <Sidebar />
        <main className="flex min-w-0 flex-1 flex-col">
          <LayoutDataContext.Provider value={{ stats: stats.data, statsError: stats.error }}>
            <Outlet />
          </LayoutDataContext.Provider>
        </main>
      </div>
    </div>
  );
}