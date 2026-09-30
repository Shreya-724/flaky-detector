import { useEffect, useState } from "react";

interface Line {
  text: string;
  tone?: "prompt" | "pass" | "flaky" | "dim";
}

const SCRIPT: Line[] = [
  { text: "$ pytest --junitxml=report.xml", tone: "prompt" },
  { text: "....F........", tone: "pass" },
  { text: "$ flaky-detector submit report.xml", tone: "prompt" },
  { text: "Created run 42: 13 tests, 13 scored.", tone: "dim" },
  { text: "! tests.test_search::test_results_load_in_time just went flaky (77.8)", tone: "flaky" },
];

const CHAR_MS = 18;
const LINE_PAUSE_MS = 550;
const LOOP_PAUSE_MS = 2400;

const TONE_CLASS: Record<NonNullable<Line["tone"]>, string> = {
  prompt: "text-neutral-300",
  pass: "text-pass",
  flaky: "text-flaky",
  dim: "text-neutral-500",
};

/** A small looping "typed terminal" used as the on-theme animated visual on
 * the landing and auth pages. Respects prefers-reduced-motion by just
 * rendering the finished script statically, no animation. */
export default function TerminalDemo() {
  const [lineIndex, setLineIndex] = useState(0);
  const [charIndex, setCharIndex] = useState(0);
  // State (not a ref) so it's safe to read during render. The lazy initializer runs once.
  const [reducedMotion] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );

  useEffect(() => {
    if (reducedMotion) return undefined;
    const line = SCRIPT[lineIndex];
    let timer: number;

    if (charIndex < line.text.length) {
      timer = window.setTimeout(() => setCharIndex((c) => c + 1), CHAR_MS);
    } else if (lineIndex < SCRIPT.length - 1) {
      timer = window.setTimeout(() => {
        setLineIndex((i) => i + 1);
        setCharIndex(0);
      }, LINE_PAUSE_MS);
    } else {
      timer = window.setTimeout(() => {
        setLineIndex(0);
        setCharIndex(0);
      }, LOOP_PAUSE_MS);
    }
    return () => window.clearTimeout(timer);
  }, [lineIndex, charIndex, reducedMotion]);

  const visibleLines = reducedMotion
    ? SCRIPT
    : SCRIPT.slice(0, lineIndex + 1).map((l, i) =>
        i === lineIndex ? { ...l, text: l.text.slice(0, charIndex) } : l,
      );
  const isTyping = !reducedMotion && charIndex < SCRIPT[lineIndex].text.length;

  return (
    <div className="border border-neutral-800 bg-panel p-4 shadow-[0_0_50px_-16px_rgba(245,158,11,0.18)]">
      <div className="mb-3 flex items-center gap-1.5 border-b border-neutral-800 pb-2">
        <span className="h-2.5 w-2.5 rounded-full bg-neutral-700" />
        <span className="h-2.5 w-2.5 rounded-full bg-neutral-700" />
        <span className="h-2.5 w-2.5 rounded-full bg-neutral-700" />
        <span className="ml-2 text-neutral-600">ci</span>
      </div>
      <div className="min-h-30 leading-6">
        {visibleLines.map((l, i) => (
          <div key={i} className={TONE_CLASS[l.tone ?? "prompt"]}>
            {l.text}
            {i === lineIndex && isTyping && <span className="animate-blink">▍</span>}
          </div>
        ))}
      </div>
    </div>
  );
}