import { useState } from "react";
import { authPaths, splitName, type QuarantineResponse, type TestRow } from "../api";
import { useAuth } from "../auth";

export default function QuarantineControl({
  slug,
  test,
  onChange,
}: {
  slug: string;
  test: TestRow;
  onChange: (next: Pick<TestRow, "quarantined" | "quarantined_at">) => void;
}) {
  const { authFetch } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const [, fn] = splitName(test.name);
  const snippet = `@pytest.mark.skip(reason="quarantined: flaky-detector #${test.id}")\ndef ${fn}():`;

  async function toggle() {
    setError(null);
    setBusy(true);
    try {
      const body = await authFetch<QuarantineResponse>(authPaths.quarantineTest(slug, test.id), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quarantined: !test.quarantined }),
      });
      onChange({ quarantined: body.quarantined, quarantined_at: body.quarantined_at });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update quarantine status.");
    } finally {
      setBusy(false);
    }
  }

  async function copySnippet() {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      // Clipboard can be blocked; the snippet is still visible to copy by hand.
    }
  }

  return (
    <div className="border-t border-neutral-800 px-3 py-2">
      <div className="flex items-center justify-between">
        <span className="text-neutral-500">
          {test.quarantined ? "Quarantined — excluded while the flakiness is fixed" : "Not quarantined"}
        </span>
        <button
          type="button"
          onClick={() => void toggle()}
          disabled={busy}
          className={`border px-2 py-1 outline-none disabled:opacity-50 ${
            test.quarantined
              ? "border-neutral-700 text-neutral-300 hover:border-flaky hover:text-flaky"
              : "border-flaky/60 bg-flaky/10 text-flaky hover:bg-flaky/20"
          }`}
        >
          {busy ? "updating…" : test.quarantined ? "unquarantine" : "quarantine this test"}
        </button>
      </div>
      {error && <p className="mt-2 text-flaky">{error}</p>}

      {test.quarantined && (
        <div className="mt-2">
          <div className="flex items-center justify-between text-neutral-500">
            <span>Paste this above the test to skip it in CI until it's fixed</span>
            <button
              type="button"
              onClick={() => void copySnippet()}
              className="text-neutral-400 outline-none hover:text-flaky focus-visible:text-flaky"
            >
              {copied ? "copied" : "copy snippet"}
            </button>
          </div>
          <pre className="mt-1 overflow-x-auto border border-neutral-800 bg-black p-2 text-[11px] leading-5 text-neutral-300">
            {snippet}
          </pre>
        </div>
      )}
    </div>
  );
}