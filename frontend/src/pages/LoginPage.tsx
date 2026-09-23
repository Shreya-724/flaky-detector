import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import AuthLayout from "./AuthLayout";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: string } };
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username, password);
      navigate(location.state?.from ?? "/projects", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not log in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Log in">
      <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-neutral-500">username</span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
            className="border border-neutral-800 bg-black px-2 py-1.5 text-neutral-100 outline-none focus:border-flaky"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-neutral-500">password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
            className="border border-neutral-800 bg-black px-2 py-1.5 text-neutral-100 outline-none focus:border-flaky"
          />
        </label>
        {error && <p className="text-flaky">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="mt-1 border border-flaky/60 bg-flaky/10 py-1.5 text-flaky outline-none hover:bg-flaky/20 focus-visible:bg-flaky/20 disabled:opacity-50"
        >
          {busy ? "logging in…" : "log in"}
        </button>
      </form>
      <p className="mt-4 text-neutral-500">
        No account?{" "}
        <Link to="/register" className="text-neutral-300 underline outline-none hover:text-flaky focus-visible:text-flaky">
          sign up
        </Link>
      </p>
    </AuthLayout>
  );
}