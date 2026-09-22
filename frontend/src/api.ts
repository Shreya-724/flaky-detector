export const API_BASE: string = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
export const PROJECT_SLUG: string = import.meta.env.VITE_PROJECT_SLUG ?? "demo-seed";
export const PAGE_SIZE = 25; // keep in sync with StandardPagination.page_size on the backend

export type Status = "flaky" | "suspect" | "stable" | "insufficient_data";

export interface TestRow {
id: number;
name: string;
status: Status;
flakiness_score: number | null;
executions: number;
conflict_commits: number;
  failure_rate: number; // fraction, 0..1
  flip_rate: number; // fraction, 0..1
last_seen: string | null;
}

export interface Page<T> {
count: number;
next: string | null;
previous: string | null;
results: T[];
}

export interface Stats {
  project: { name: string; slug: string; default_branch: string };
  window_days: number;
  tests: { total: number } & Record<Status, number>;
  runs: { total: number; commits: number };
  flaky_failures: number;
  wasted_runs: number;
  wasted_ci_minutes: number;
  failure_rate?: { last_7d: number | null; prev_7d: number | null; delta_pp: number | null };
}

export interface DailyPoint {
  date: string;
  runs: number;
  failures: number;
}

export interface RecentRun {
  executed_at: string;
  outcome: "passed" | "failed" | "error";
  commit: string;
  branch: string;
  attempt: number;
  duration_ms: number | null;
}

export interface TestDetailResponse {
  test: TestRow;
  daily: DailyPoint[];
  recent: RecentRun[];
  errors: { group_id: number; message: string; count: number; last_seen: string }[];
}

export interface ErrorGroupRow {
  id: number;
  message: string;
  occurrences: number;
  tests_affected: number;
  first_seen: string;
  last_seen: string;
}

const base = `/api/projects/${PROJECT_SLUG}`;

export const paths = {
  stats: `${base}/stats/`,
  errors: `${base}/errors/`,
  tests: (q: { statuses: Status[]; search: string; page: number }): string => {
    const params = new URLSearchParams();
    if (q.statuses.length > 0) params.set("status", q.statuses.join(","));
    if (q.search) params.set("search", q.search);
    params.set("page", String(q.page));
    return `${base}/tests/?${params.toString()}`;
  },
  test: (id: number): string => `${base}/tests/${id}/`,
};

export async function fetchJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { signal, headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export const STATUS_LABEL: Record<Status, string> = {
  flaky: "flaky",
  suspect: "suspect",
  stable: "stable",
  insufficient_data: "no data",
};

export const STATUS_TEXT: Record<Status, string> = {
  flaky: "text-flaky",
  suspect: "text-flaky/60",
  stable: "text-neutral-500",
  insufficient_data: "text-neutral-600",
};

export const STATUS_BAR: Record<Status, string> = {
  flaky: "bg-flaky",
  suspect: "bg-flaky/50",
  stable: "bg-neutral-700",
  insufficient_data: "bg-neutral-800",
};

/** "tests.test_cart::test_checkout" -> ["tests.test_cart", "test_checkout"] */
export function splitName(name: string): [string, string] {
  const i = name.indexOf("::");
  return i === -1 ? ["", name] : [name.slice(0, i), name.slice(i + 2)];
}