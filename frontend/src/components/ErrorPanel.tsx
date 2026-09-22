import { useState, type ReactNode } from "react";
import type { ErrorGroupRow } from "../api";

// Dim "syntax highlighting": exception names, quoted strings, numbers.
const TOKEN = /(\b[A-Z][A-Za-z]*(?:Error|Exception|Warning)\b)|('[^']*'|"[^"]*")|(\b\d+(?:\.\d+)?(?:ms|s)?\b)/g;

function highlight(line: string): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  for (const m of line.matchAll(TOKEN)) {
    const start = m.index ?? 0;
    if (start > last) out.push(line.slice(last, start));
    const tone = m[1] ? "text-flaky/80" : m[2] ? "text-pass/70" : "text-neutral-200";
    out.push(
      <span key={start} className={tone}>
        {m[0]}
      </span>,
    );
    last = start + m[0].length;
  }
  if (last < line.length) out.push(line.slice(last));
  return out;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      // Clipboard access can be blocked (insecure origin or denied permission); nothing to do.
    }
  }

  return (
    <button
      type="button"
      onClick={() => void copy()}
      className="px-3 text-neutral-500 opacity-0 outline-none transition-opacity group-hover:opacity-100 hover:text-flaky focus-visible:opacity-100 motion-reduce:transition-none"
    >
      {copied ? "copied" : "copy error"}
    </button>
  );
}

const stamp = (iso: string) => iso.slice(0, 16).replace("T", " ");

export default function ErrorPanel({ groups, error }: { groups?: ErrorGroupRow[]; error?: string }) {
  const [openId, setOpenId] = useState<number | null>(null);

  return (
    <section className="bg-black">
      <div className="flex items-center justify-between border-b border-neutral-800 bg-panel px-3 py-1.5 text-neutral-500">
        <h2 className="font-normal">Failure messages, grouped by pattern</h2>
        <span>{groups ? `${groups.length} groups, most frequent first` : ""}</span>
      </div>
      {error && <p className="px-3 py-3 text-flaky">Could not load error groups: {error}</p>}
      {!groups && !error && <p className="px-3 py-3 text-neutral-500">loading</p>}
      {groups && groups.length === 0 && <p className="px-3 py-3 text-neutral-500">No failures recorded yet.</p>}
      <ul>
        {groups?.map((g) => {
          const open = openId === g.id;
          const lines = g.message.split("\n");
          const meta = `# first seen ${stamp(g.first_seen)}, last seen ${stamp(g.last_seen)}, ${g.tests_affected} ${
            g.tests_affected === 1 ? "test" : "tests"
          }`;
          return (
            <li key={g.id} className="group border-b border-neutral-900">
              <div className="flex items-center hover:bg-panel-2">
                <button
                  type="button"
                  aria-expanded={open}
                  onClick={() => setOpenId(open ? null : g.id)}
                  className="flex min-w-0 flex-1 items-center gap-3 px-3 py-1.5 text-left outline-none focus-visible:bg-panel-2"
                >
                  <span className="w-3 shrink-0 text-neutral-600">{open ? "▾" : "▸"}</span>
                  <span className="w-12 shrink-0 text-right tabular-nums text-flaky">{g.occurrences}×</span>
                  <span className="truncate text-neutral-300">{lines[0]}</span>
                </button>
                <CopyButton text={g.message} />
              </div>
              {open && (
                <pre className="overflow-x-auto border-t border-neutral-900 bg-panel py-2 text-[11px] leading-5">
                  {lines.map((line, n) => (
                    <div key={n} className="flex">
                      <span className="w-14 shrink-0 pr-3 text-right text-neutral-700 select-none">{n + 1}</span>
                      <code className="whitespace-pre-wrap text-neutral-400">{highlight(line)}</code>
                    </div>
                  ))}
                  <div className="flex">
                    <span className="w-14 shrink-0 pr-3 text-right text-neutral-700 select-none">{lines.length + 1}</span>
                    <code className="text-neutral-600">{meta}</code>
                  </div>
                </pre>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}