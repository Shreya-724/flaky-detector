import { Link } from "react-router-dom";
import { DEFAULT_PROJECT_SLUG } from "../api";
import { useAuth } from "../auth";
import TerminalDemo from "../components/TerminalDemo";

const STEPS = [
  { n: "01", title: "Upload", body: "Run pytest with --junitxml, then one flaky-detector submit in CI. That's the whole integration." },
  { n: "02", title: "Detect", body: "Every run is scored against 30 days of history the moment it lands. No batch jobs, no waiting." },
  { n: "03", title: "Fix", body: "Quarantine it, get alerted, and watch the score fall as the real fix goes in." },
];

const FEATURES = [
  {
    title: "Evidence, not vibes",
    body: "Same-commit pass/fail conflicts, flip rate and intermittency combine into one score. A test that always fails is called broken, not flaky.",
  },
  {
    title: "Quarantine",
    body: "One click marks a test quarantined and hands you a ready pytest skip snippet to paste above it.",
  },
  {
    title: "Alerts when it happens",
    body: "Slack or email the moment a test first crosses into flaky. Fired at ingest, not from a nightly scan.",
  },
  {
    title: "A badge for your README",
    body: "An embeddable SVG showing the live flaky-test count for any public project.",
  },
];

const linkBase = "outline-none transition-colors duration-150";

export default function LandingPage() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-black font-mono text-neutral-100">
      <header className="flex items-center justify-between border-b border-neutral-800 px-4 py-3 sm:px-8">
        <Link to="/" className={`${linkBase} text-sm font-semibold hover:text-flaky focus-visible:text-flaky`}>
          <span className="text-flaky">●</span> flaky-detector
        </Link>
        <nav className="flex items-center gap-4 text-xs">
          <Link
            to={`/p/${DEFAULT_PROJECT_SLUG}`}
            className={`${linkBase} text-neutral-400 hover:text-flaky focus-visible:text-flaky`}
          >
            live demo
          </Link>
          {isAuthenticated ? (
            <Link
              to="/projects"
              className={`${linkBase} border border-flaky/60 bg-flaky/10 px-3 py-1 text-flaky hover:bg-flaky/20 focus-visible:bg-flaky/20`}
            >
              my projects
            </Link>
          ) : (
            <>
              <Link to="/login" className={`${linkBase} text-neutral-400 hover:text-flaky focus-visible:text-flaky`}>
                log in
              </Link>
              <Link
                to="/register"
                className={`${linkBase} border border-flaky/60 bg-flaky/10 px-3 py-1 text-flaky hover:bg-flaky/20 focus-visible:bg-flaky/20`}
              >
                sign up
              </Link>
            </>
          )}
        </nav>
      </header>

      <section className="mx-auto grid max-w-5xl grid-cols-1 gap-10 px-4 py-16 sm:px-8 lg:grid-cols-2 lg:items-center lg:py-24">
        <div className="animate-rise-in">
          <p className="mb-4 flex items-center gap-2 text-[11px] text-neutral-500">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-flaky motion-reduce:animate-none" />
            scoring real CI history, run by run
          </p>
          <h1 className="text-3xl font-semibold leading-tight sm:text-4xl">
            Stop guessing which tests are <span className="text-flaky">flaky</span>.
          </h1>
          <p className="mt-4 max-w-md text-sm leading-relaxed text-neutral-400">
            flaky-detector reads your CI results, scores every test from its actual history, and tells your team
            the moment one crosses the line. No more re-run and hope.
          </p>
          <div className="mt-7 flex flex-wrap items-center gap-3 text-xs">
            <Link
              to={isAuthenticated ? "/projects" : "/register"}
              className={`${linkBase} border border-flaky/60 bg-flaky/10 px-4 py-2 text-flaky hover:bg-flaky/20 focus-visible:bg-flaky/20`}
            >
              {isAuthenticated ? "open my projects →" : "get started free →"}
            </Link>
            <Link
              to={`/p/${DEFAULT_PROJECT_SLUG}`}
              className={`${linkBase} border border-neutral-800 px-4 py-2 text-neutral-300 hover:border-flaky hover:text-flaky focus-visible:border-flaky`}
            >
              view live demo
            </Link>
          </div>
          <p className="mt-4 text-[11px] text-neutral-600">pip install flaky-detector-cli · zero dependencies</p>
        </div>
        <div className="animate-rise-in text-xs" style={{ animationDelay: "120ms" }}>
          <TerminalDemo />
        </div>
      </section>

      <section className="border-y border-neutral-800 bg-panel">
        <div className="mx-auto max-w-5xl px-4 py-14 sm:px-8">
          <h2 className="mb-8 text-sm font-normal text-[#f59e0b]">HOW IT WORKS</h2>
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
            {STEPS.map((s, i) => (
              <div key={s.n} className="animate-rise-in" style={{ animationDelay: `${i * 90}ms` }}>
                <div className="text-flaky">{s.n}</div>
                <div className="mt-1 text-neutral-100">{s.title}</div>
                <p className="mt-1 text-xs leading-relaxed text-neutral-500">{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-14 sm:px-8">
        <h2 className="mb-8 text-sm font-normal text-[#f59e0b]">WHAT YOU GET</h2>
        <div className="grid grid-cols-1 divide-y divide-neutral-800 border border-neutral-800 sm:grid-cols-2 sm:divide-x sm:divide-y-0">
          {FEATURES.map((f) => (
            <div key={f.title} className="p-4">
              <div className="text-sm text-neutral-100">{f.title}</div>
              <p className="mt-1 text-xs leading-relaxed text-neutral-500">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-neutral-800 px-4 py-6 text-center text-[11px] text-neutral-600 sm:px-8">
        2026 flaky-detector @ Shreya Bhattarai.
      </footer>
    </div>
  );
}