import type { ReactNode } from "react";
import { Link } from "react-router-dom";

/** Shared shell for the login/register cards: same theme, no sidebar (there's nothing to navigate yet). */
export default function AuthLayout({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-black px-4 font-mono text-xs text-neutral-100">
      <Link to="/" className="mb-6 font-semibold text-neutral-300 outline-none hover:text-flaky focus-visible:text-flaky">
        flaky-detector
      </Link>
      <div className="w-full max-w-sm border border-neutral-800 bg-panel p-4">
        <h1 className="mb-4 text-neutral-100">{title}</h1>
        {children}
      </div>
    </div>
  );
}