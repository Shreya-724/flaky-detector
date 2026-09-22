import { useEffect, useState } from "react";
import { fetchJson } from "./api";

interface FetchState<T> {
  path: string | null;
  data?: T;
  error?: string;
}

/**
 * Fetch JSON for `path` (null = do nothing). With keepPrevious, the last
 * response stays on screen while the next one loads, so tables don't flicker.
 */
export function useFetch<T>(path: string | null, keepPrevious = false) {
  const [state, setState] = useState<FetchState<T>>({ path: null });

  useEffect(() => {
    if (path === null) return undefined;
    const controller = new AbortController();
    fetchJson<T>(path, controller.signal)
      .then((data) => setState({ path, data }))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setState({ path, error: err instanceof Error ? err.message : String(err) });
      });
    return () => controller.abort();
  }, [path]);

  const current = state.path === path ? state : undefined;
  const shown = current ?? (keepPrevious ? state : undefined);
  return {
    data: shown?.data,
    error: current?.error,
    loading: path !== null && current === undefined,
  };
}

export function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}