"""
Flakiness scoring + error fingerprinting.

Pure Python on purpose: no Django imports, so you can unit test it with plain
pytest and feed it hand-built data.

Score (0-100) = 100 * ( W_CONFLICT * A  +  w * (W_FLIP * B + W_INTERMITTENT * C) )

A  conflict evidence : same commit (+ same job) produced BOTH pass and fail.
                        This is direct proof, so it needs no minimum sample.
                        A = 1 - exp(-conflicts / CONFLICT_K)   (saturating)
B  flip rate         : how often consecutive default-branch results change
                        pass<->fail, scaled so FLIP_SATURATION (30%) = maxed out.
  C  intermittency     : 4 * p * (1 - p), p = failure rate. 0 for always-pass
                        AND always-fail (a consistently failing test is
                         *broken*, not flaky), peaks at p = 0.5.
w  sample weight     : min(1, executions / FULL_CONFIDENCE_AT). B and C are
                        statistical, so they're damped when data is thin.

All weights/thresholds below are starting heuristics. Tune them against your
seeded demo data, and say so in the README.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

# ---- tunables --------------------------------------------------------------
MIN_EXECUTIONS = 10          # below this (and no conflicts) -> insufficient_data
FULL_CONFIDENCE_AT = 30      # executions needed for sample weight w = 1
CONFLICT_K = 1.5             # bigger = need more conflicts to saturate A
FLIP_SATURATION = 0.30       # flip rate at which B = 1
W_CONFLICT = 0.60
W_FLIP = 0.25
W_INTERMITTENT = 0.15
FLAKY_AT = 50                # score >= this  -> "flaky"
SUSPECT_AT = 20              # score >= this  -> "suspect"


@dataclass(frozen=True)
class Execution:
    """One time a test actually ran (skips must be filtered out by the caller)."""
    commit_key: str          # f"{commit_sha}:{job_name}" so matrix jobs don't collide
    passed: bool             # treat error as failed
    executed_at: datetime
    on_default_branch: bool


@dataclass(frozen=True)
class FlakinessResult:
    score: float | None
    status: str              # flaky | suspect | stable | insufficient_data
    executions: int
    commits: int
    conflict_commits: int
    failure_rate: float
    flip_rate: float


def compute_flakiness(executions: list[Execution]) -> FlakinessResult:
    n = len(executions)
    if n == 0:
        return FlakinessResult(None, "insufficient_data", 0, 0, 0, 0.0, 0.0)

    # --- A: conflicts -------------------------------------------------------
    outcomes_by_commit: dict[str, set[bool]] = defaultdict(set)
    for e in executions:
        outcomes_by_commit[e.commit_key].add(e.passed)
    commits = len(outcomes_by_commit)
    conflicts = sum(1 for o in outcomes_by_commit.values() if len(o) == 2)

    # --- gate ---------------------------------------------------------------
    if n < MIN_EXECUTIONS and conflicts == 0:
        return FlakinessResult(None, "insufficient_data", n, commits, 0, 0.0, 0.0)

    a = 1 - math.exp(-conflicts / CONFLICT_K)

    # --- B: flip rate (default branch only, so PR churn doesn't pollute it) --
    main = sorted((e for e in executions if e.on_default_branch),
                key=lambda e: e.executed_at)
    if len(main) >= 2:
        flips = sum(1 for prev, cur in zip(main, main[1:]) if prev.passed != cur.passed)
        flip_rate = flips / (len(main) - 1)
    else:
        flip_rate = 0.0
    b = min(flip_rate / FLIP_SATURATION, 1.0)

    # --- C: intermittency ---------------------------------------------------
    p = sum(1 for e in executions if not e.passed) / n
    c = 4 * p * (1 - p)

    # --- combine ------------------------------------------------------------
    w = min(1.0, n / FULL_CONFIDENCE_AT)
    score = 100 * (W_CONFLICT * a + w * (W_FLIP * b + W_INTERMITTENT * c))
    score = round(min(score, 100.0), 1)

    if score >= FLAKY_AT:
        status = "flaky"
    elif score >= SUSPECT_AT:
        status = "suspect"
    else:
        status = "stable"

    return FlakinessResult(score, status, n, commits, conflicts, round(p, 4), round(flip_rate, 4))


# ---- error fingerprinting ---------------------------------------------------
# Goal: "Timeout after 5023ms at 0x7f3a..." and "Timeout after 4987ms at 0x7f9b..."
# should land in the same group. Strip the parts that change between runs.
_NORMALIZERS = [
    (re.compile(r"0x[0-9a-fA-F]+"), "<ADDR>"),
    (re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"), "<UUID>"),
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?Z?"), "<TS>"),
    (re.compile(r"(/[\w.\-]+)+"), "<PATH>"),
    (re.compile(r"\d+"), "<N>"),
    (re.compile(r"\s+"), " "),
]


def normalize_error(message: str) -> str:
    text = message.strip()
    for pattern, repl in _NORMALIZERS:
        text = pattern.sub(repl, text)
    return text[:500]


def error_fingerprint(message: str) -> str:
    return hashlib.sha1(normalize_error(message).encode()).hexdigest()
