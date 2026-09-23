import { Outlet, useParams } from "react-router-dom";
import { API_BASE, paths, type Stats } from "./api";
import AccountMenu from "./components/AccountMenu";
import Sidebar from "./components/Sidebar";
import { useFetch } from "./hooks";
import { LayoutDataContext } from "./layoutContext";

export default function Layout() {
  const { slug } = useParams<{ slug: string }>();
  const stats = useFetch<Stats>(slug ? paths.stats(slug) : null);

  return (
    <div className="flex min-h-screen flex-col bg-black font-mono text-xs text-neutral-100">
      <header className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-neutral-800 bg-panel px-3 py-2">
        <h1 className="font-semibold">
          flaky-detector <span className="font-normal text-neutral-500">/ {slug}</span>
        </h1>
        <div className="flex items-center gap-3">
          <span className="text-neutral-500">
            default branch {stats.data?.project.default_branch ?? "–"}, scoring window{" "}
            {stats.data?.window_days ?? "–"}d
          </span>
          <AccountMenu />
        </div>
      </header>

      {stats.error && (
        <p className="border-b border-neutral-800 bg-panel px-3 py-2 text-flaky">
          Can't load project "{slug}" from {API_BASE} ({stats.error}). If you just created it, make sure it's
          marked public, or{" "}
          <a href="/login" className="underline hover:text-flaky/80">
            log in
          </a>{" "}
          to view your private dashboard.
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