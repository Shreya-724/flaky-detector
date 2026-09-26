import { useEffect, useState } from "react";
import { Outlet, useParams } from "react-router-dom";
import { API_BASE, authPaths, paths, type OwnedProject, type Stats } from "./api";
import { useAuth } from "./auth";
import AccountMenu from "./components/AccountMenu";
import Sidebar from "./components/Sidebar";
import { useFetch } from "./hooks";
import { LayoutDataContext } from "./layoutContext";

export default function Layout() {
  const { slug } = useParams<{ slug: string }>();
  const stats = useFetch<Stats>(slug ? paths.stats(slug) : null);
  const { isAuthenticated, authFetch } = useAuth();

  const [isOwner, setIsOwner] = useState<boolean | undefined>(undefined);
  useEffect(() => {
    setIsOwner(undefined);
    if (!isAuthenticated || !slug) return;
    let cancelled = false;
    authFetch<OwnedProject>(authPaths.myProject(slug))
      .then(() => {
        if (!cancelled) setIsOwner(true);
      })
      .catch(() => {
        if (!cancelled) setIsOwner(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slug, isAuthenticated, authFetch]);

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
          <LayoutDataContext.Provider value={{ stats: stats.data, statsError: stats.error, isOwner }}>
            <Outlet />
          </LayoutDataContext.Provider>
        </main>
      </div>
    </div>
  );
}