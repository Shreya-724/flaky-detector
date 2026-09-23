import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import AuthLayout from "./AuthLayout";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await register(username, email, password);
      navigate("/projects", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create an account.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Create an account">
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
          <span className="text-neutral-500">email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
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
            autoComplete="new-password"
            required
            minLength={8}
            className="border border-neutral-800 bg-black px-2 py-1.5 text-neutral-100 outline-none focus:border-flaky"
          />
          <span className="text-[11px] text-neutral-600">At least 8 characters, not too common or predictable.</span>
        </label>
        {error && <p className="text-flaky">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="mt-1 border border-flaky/60 bg-flaky/10 py-1.5 text-flaky outline-none hover:bg-flaky/20 focus-visible:bg-flaky/20 disabled:opacity-50"
        >
          {busy ? "creating…" : "create account"}
        </button>
      </form>
      <p className="mt-4 text-neutral-500">
        Already have an account?{" "}
        <Link to="/login" className="text-neutral-300 underline outline-none hover:text-flaky focus-visible:text-flaky">
          log in
        </Link>
      </p>
    </AuthLayout>
  );
}