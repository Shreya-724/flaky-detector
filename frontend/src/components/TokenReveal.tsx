import { useState } from "react";

/**
 * Shows a freshly (re)generated project token exactly once, with a copy
 * button and a ready-to-paste GitHub Actions snippet. The parent is
 * responsible for not holding onto the token anywhere else.
 */
export default function TokenReveal({ slug, token }: { slug: string; token: string }) {
  const [copiedToken, setCopiedToken] = useState(false);
  const [copiedSnippet, setCopiedSnippet] = useState(false);

  const snippet = `- name: Upload test results to flaky-detector
  if: always()
  run: |
    curl -sS -X POST "\${{ vars.FLAKY_DETECTOR_URL }}/api/ingest/" \\
      -H "Authorization: Bearer \${{ secrets.FLAKY_DETECTOR_TOKEN }}" \\
      -F "report=@report.xml" \\
      -F "run_id=\${{ github.run_id }}" \\
      -F "run_attempt=\${{ github.run_attempt }}" \\
      -F "commit_sha=\${{ github.sha }}" \\
      -F "branch=\${{ github.ref_name }}"

# Add these in your repo's Settings -> Secrets and variables -> Actions:
#   FLAKY_DETECTOR_TOKEN (secret) = ${token}
#   FLAKY_DETECTOR_URL   (variable) = <where you deploy this backend>`;

  async function copy(text: string, mark: (v: boolean) => void) {
    try {
      await navigator.clipboard.writeText(text);
      mark(true);
      window.setTimeout(() => mark(false), 1200);
    } catch {
      // Clipboard can be blocked; the value is still selectable/visible.
    }
  }

  return (
    <div className="border border-flaky/40 bg-panel p-4">
      <p className="text-flaky">
        Project token for <span className="text-neutral-100">{slug}</span> — copy it now, it won't be shown
        again.
      </p>

      <div className="mt-3 flex items-center gap-2">
        <code className="min-w-0 flex-1 overflow-x-auto whitespace-nowrap border border-neutral-800 bg-black px-2 py-1.5 text-neutral-100">
          {token}
        </code>
        <button
          type="button"
          onClick={() => void copy(token, setCopiedToken)}
          className="shrink-0 border border-neutral-700 px-2 py-1.5 text-neutral-300 outline-none hover:border-flaky hover:text-flaky focus-visible:border-flaky"
        >
          {copiedToken ? "copied" : "copy token"}
        </button>
      </div>

      <div className="mt-4 flex items-center justify-between text-neutral-500">
        <span>Paste this step into your GitHub Actions workflow, after your test step</span>
        <button
          type="button"
          onClick={() => void copy(snippet, setCopiedSnippet)}
          className="text-neutral-400 outline-none hover:text-flaky focus-visible:text-flaky"
        >
          {copiedSnippet ? "copied" : "copy snippet"}
        </button>
      </div>
      <pre className="mt-1 overflow-x-auto border border-neutral-800 bg-black p-3 text-[11px] leading-5 text-neutral-300">
        {snippet}
      </pre>
    </div>
  );
}