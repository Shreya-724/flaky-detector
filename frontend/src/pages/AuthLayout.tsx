import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import TerminalDemo from "../components/TerminalDemo";

/** Split-screen shell for login/register: pitch + animated terminal on the
 * left (desktop only), the form on the right. Same theme as the dashboard. */
export default function AuthLayout({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="grid min-h-screen grid-cols-1 bg-black font-mono text-xs text-neutral-100 lg:grid-cols-2">
      <div className="hidden flex-col justify-center border-r border-neutral-800 bg-panel p-10 lg:flex">
        <Link
          to="/"
          className="mb-8 w-fit text-sm font-semibold text-neutral-300 outline-none transition-colors duration-150 hover:text-flaky focus-visible:text-flaky"
        >
          <span className="text-flaky">●</span> flaky-detector
        </Link>
        <p className="mb-6 max-w-sm text-sm leading-relaxed text-neutral-400">
          Detect flaky tests from real CI history: same-commit conflicts, flip rate and intermittency, scored on
          every run.
        </p>
        <div className="max-w-md">
          <TerminalDemo />
        </div>
      </div>

      <div className="flex flex-col items-center justify-center px-4 py-10">
        <Link
          to="/"
          className="mb-6 font-semibold text-neutral-300 outline-none transition-colors duration-150 hover:text-flaky focus-visible:text-flaky lg:hidden"
        >
          <span className="text-flaky">●</span> flaky-detector
        </Link>
        <div className="animate-rise-in w-full max-w-sm border border-neutral-800 bg-panel p-5">
          <h1 className="mb-4 text-sm text-neutral-100">{title}</h1>
          {children}
        </div>
      </div>
    </div>
  );
}