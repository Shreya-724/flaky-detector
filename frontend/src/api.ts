export const API_BASE: string = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
// Fallback project shown at "/" before you've created your own. Not used anywhere else;
// every dashboard route carries its own slug (see App.tsx's "/p/:slug" routes).
export const DEFAULT_PROJECT_SLUG: string = import.meta.env.VITE_PROJECT_SLUG ?? "demo-seed";
export const PAGE_SIZE = 25; // keep in sync with StandardPagination.page_size on the backend

export type Status = "flaky" | "suspect" | "stable" | "insufficient_data";

export interface TestRow {
  id: number;
  name: string;
  status: Status;
  flakiness_score: number | null;
  executions: number;
  conflict_commits: number;
  failure_rate: number;
  flip_rate: number;
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

/** Every dashboard endpoint is scoped to a project slug, taken from the "/p/:slug" route param. */
export const paths = {
  stats: (slug: string): string => `/api/projects/${slug}/stats/`,
  errors: (slug: string): string => `/api/projects/${slug}/errors/`,
  tests: (slug: string, q: { statuses: Status[]; search: string; page: number }): string => {
    const params = new URLSearchParams();
    if (q.statuses.length > 0) params.set("status", q.statuses.join(","));
    if (q.search) params.set("search", q.search);
    params.set("page", String(q.page));
    return `/api/projects/${slug}/tests/?${params.toString()}`;
  },
  test: (slug: string, id: number): string => `/api/projects/${slug}/tests/${id}/`,
};

export async function fetchJson<T>(path: string, signal?: AbortSignal, bearer?: string): Promise<T> {
  const headers: HeadersInit = { Accept: "application/json" };
  if (bearer) headers.Authorization = `Bearer ${bearer}`;
  const res = await fetch(`${API_BASE}${path}`, { signal, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(firstErrorMessageInline(body) ?? `${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => null);
    throw new Error(firstErrorMessageInline(errBody) ?? `${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

// Duplicated (tiny) rather than importing from auth.tsx, to avoid a circular import
// between api.ts and auth.tsx.
function firstErrorMessageInline(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;
  const obj = body as Record<string, unknown>;
  if (typeof obj.detail === "string") return obj.detail;
  for (const value of Object.values(obj)) {
    if (typeof value === "string") return value;
    if (Array.isArray(value) && typeof value[0] === "string") return value[0] as string;
  }
  return null;
}

// ---- account / project-management API (JWT-authenticated, separate from the
// public, unauthenticated dashboard endpoints above) --------------------------

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface MeResponse {
  username: string;
  email: string;
}

export interface OwnedProject {
  id: number;
  name: string;
  slug: string;
  repo: string;
  default_branch: string;
  is_public: boolean;
  created_at: string;
}

export interface CreateProjectResponse {
  project: OwnedProject;
  token: string;
}

export const authPaths = {
  register: "/api/auth/register/",
  login: "/api/auth/token/",
  refresh: "/api/auth/token/refresh/",
  me: "/api/auth/me/",
  myProjects: "/api/auth/projects/",
  myProject: (slug: string): string => `/api/auth/projects/${slug}/`,
  regenerateToken: (slug: string): string => `/api/auth/projects/${slug}/regenerate-token/`,
};

export function splitName(name: string): [string, string] {
  const i = name.indexOf("::");
  return i === -1 ? ["", name] : [name.slice(0, i), name.slice(i + 2)];
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