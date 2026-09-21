"""
Fake CI history for demos and screenshots. Pure Python (no Django), so the
generator can be unit tested; the `seed_demo` management command feeds its
output into the real ingest pipeline.

The cast of tests is chosen so the dashboard tells a clear story:
- a few tests that are flaky at different rates (should be flagged)
- one test that always fails       (broken, should NOT be flagged as flaky)
- one test broken for a while, then fixed (should NOT be flagged as flaky)
- many stable tests
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .junit_parser import FAILED, PASSED, ParsedCase

_STABLE_TESTS = {
    "test_cart": ["test_add_item", "test_remove_item", "test_apply_coupon", "test_empty_cart"],
    "test_auth": ["test_login", "test_logout", "test_signup", "test_token_refresh"],
    "test_search": ["test_basic_query", "test_filters", "test_pagination", "test_empty_query"],
    "test_orders": ["test_create_order", "test_cancel_order", "test_order_history"],
    "test_payments": ["test_charge_card", "test_refund", "test_invalid_card"],
    "test_profile": ["test_update_name", "test_change_email", "test_delete_account"],
}

# name -> (failure probability per execution, error message template)
FLAKY_TESTS = {
    "tests.test_search::test_results_load_in_time": (0.25, "TimeoutError: waited {n}ms for element #results"),
    "tests.test_payments::test_webhook_delivery": (0.15, "ConnectionError: webhook endpoint returned 503 after {n}ms"),
    "tests.test_orders::test_concurrent_orders": (0.10, "AssertionError: expected 3 orders but found {n}"),
    "tests.test_cart::test_checkout": (0.06, "TimeoutError: waited {n}ms for element #checkout-button"),
}
ALWAYS_BROKEN = "tests.test_profile::test_avatar_upload"
BROKEN_THEN_FIXED = "tests.test_auth::test_password_reset"   # broken for a slice of the history
BROKEN_SLICE = (0.40, 0.55)                                    # fraction of commits

STABLE_NAMES = [f"tests.{mod}::{name}" for mod, names in _STABLE_TESTS.items() for name in names]
ALL_TEST_NAMES = STABLE_NAMES + list(FLAKY_TESTS) + [ALWAYS_BROKEN, BROKEN_THEN_FIXED]


@dataclass(frozen=True)
class SeedRun:
    run_id: str
    run_attempt: int
    commit_sha: str
    branch: str
    started_at: datetime
    cases: list[ParsedCase]


def generate_runs(commits=150, days=25, seed=42, retry_prob=0.7, now=None) -> list[SeedRun]:
    """History spanning `days` ending now. Keep days < 30 so it stays inside the scoring window."""
    rng = random.Random(seed)
    now = now or datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    step = timedelta(days=days) / commits
    broken_from, broken_to = int(commits * BROKEN_SLICE[0]), int(commits * BROKEN_SLICE[1])

    runs: list[SeedRun] = []
    for i in range(commits):
        sha = hashlib.sha1(f"{seed}-{i}".encode()).hexdigest()
        branch = "main" if rng.random() < 0.7 else f"feature/{rng.randint(1, 5)}"
        commit_time = start + step * i
        attempt = 1
        while True:
            cases, any_failed = [], False
            for name in ALL_TEST_NAMES:
                failed, template = False, "AssertionError: assert 200 == 500"
                if name in FLAKY_TESTS:
                    prob, template = FLAKY_TESTS[name]
                    failed = rng.random() < prob
                elif name == ALWAYS_BROKEN:
                    failed = True
                elif name == BROKEN_THEN_FIXED:
                    failed = broken_from <= i < broken_to
                    template = "KeyError: 'reset_token'"
                any_failed |= failed
                cases.append(ParsedCase(
                    name=name,
                    outcome=FAILED if failed else PASSED,
                    duration_ms=rng.randint(5, 400),
                    error_message=template.format(n=rng.randint(1000, 6000)) if failed else "",
                    file_path="",
                ))
            runs.append(SeedRun(f"seed-{i}", attempt, sha, branch,
                                commit_time + timedelta(minutes=4 * (attempt - 1)), cases))
            if any_failed and attempt < 3 and rng.random() < retry_prob:
                attempt += 1
                continue
            break
    return runs