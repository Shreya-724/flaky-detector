import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { API_BASE, authPaths, fetchJson, postJson, type AuthTokens, type MeResponse } from "./api";

const STORAGE_KEY = "fd_auth"; // { access, refresh, username } as JSON

interface StoredAuth {
  access: string;
  refresh: string;
  username: string;
}

function loadStored(): StoredAuth | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredAuth) : null;
  } catch {
    return null; // corrupt or blocked storage: just treat as logged out
  }
}

function saveStored(auth: StoredAuth | null) {
  try {
    if (auth) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(auth));
    else window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Storage can be unavailable (private browsing); the session just won't persist.
  }
}

interface AuthContextValue {
  username: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  /** fetch wrapper that attaches the access token and retries once after a silent refresh on 401 */
  authFetch: <T>(path: string, init?: RequestInit) => Promise<T>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth() must be used inside <AuthProvider>");
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<StoredAuth | null>(() => loadStored());

  useEffect(() => saveStored(auth), [auth]);

  async function refreshAccess(current: StoredAuth): Promise<string> {
    const tokens = await postJson<AuthTokens>(authPaths.refresh, { refresh: current.refresh });
    const next = { ...current, access: tokens.access };
    setAuth(next);
    return tokens.access;
  }

  async function authFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
    if (!auth) throw new Error("Not logged in.");
    const withToken = (token: string): RequestInit => ({
      ...init,
      headers: { ...(init.headers ?? {}), Authorization: `Bearer ${token}` },
    });

    let res = await fetch(`${API_BASE}${path}`, withToken(auth.access));
    if (res.status === 401) {
      try {
        const newAccess = await refreshAccess(auth);
        res = await fetch(`${API_BASE}${path}`, withToken(newAccess));
      } catch {
        setAuth(null);
        throw new Error("Your session expired. Please log in again.");
      }
    }
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(firstErrorMessage(body) ?? `${res.status} ${res.statusText}`);
    }
    return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
  }

  async function login(username: string, password: string) {
    const tokens = await postJson<AuthTokens>(authPaths.login, { username, password });
    const me = await fetchJson<MeResponse>(authPaths.me, undefined, tokens.access);
    setAuth({ access: tokens.access, refresh: tokens.refresh, username: me.username });
  }

  async function register(username: string, email: string, password: string) {
    const body = await postJson<AuthTokens & { username: string }>(authPaths.register, {
      username,
      email,
      password,
    });
    setAuth({ access: body.access, refresh: body.refresh, username: body.username });
  }

  function logout() {
    setAuth(null);
  }

  return (
    <AuthContext.Provider
      value={{
        username: auth?.username ?? null,
        isAuthenticated: auth !== null,
        login,
        register,
        logout,
        authFetch,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/** Pulls a readable message out of a DRF error body: field errors, {"detail": "..."}, or a plain string. */
export function firstErrorMessage(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;
  const obj = body as Record<string, unknown>;
  if (typeof obj.detail === "string") return obj.detail;
  for (const value of Object.values(obj)) {
    if (typeof value === "string") return value;
    if (Array.isArray(value) && typeof value[0] === "string") return value[0] as string;
  }
  return null;
}