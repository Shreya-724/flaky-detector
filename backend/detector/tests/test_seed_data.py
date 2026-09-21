from collections import defaultdict
from datetime import datetime, timedelta, timezone

from detector.scoring import Execution, compute_flakiness
from detector.seed_data import (
    ALWAYS_BROKEN,
    BROKEN_THEN_FIXED,
    FLAKY_TESTS,
    STABLE_NAMES,
    generate_runs,
)

NOW = datetime(2026, 9, 1, tzinfo=timezone.utc)


def classify(seed=42):
    executions = defaultdict(list)
    for run in generate_runs(seed=seed, now=NOW):
        for case in run.cases:
            executions[case.name].append(
                Execution(f"{run.commit_sha}:", case.outcome == "passed",
                        run.started_at, run.branch == "main")
            )
    return {name: compute_flakiness(ex) for name, ex in executions.items()}


def test_flaky_tests_are_flagged_as_flaky():
    results = classify()
    for name in FLAKY_TESTS:
        assert results[name].status == "flaky", (name, results[name])


def test_always_failing_test_is_not_called_flaky():
    assert classify()[ALWAYS_BROKEN].status == "stable"


def test_broken_then_fixed_test_is_not_called_flaky():
    assert classify()[BROKEN_THEN_FIXED].status != "flaky"


def test_stable_tests_stay_stable():
    results = classify()
    assert all(results[name].status == "stable" for name in STABLE_NAMES)


def test_same_seed_gives_same_history():
    def fingerprint(runs):
        return [(r.run_id, r.run_attempt, [(c.outcome, c.error_message) for c in r.cases]) for r in runs]

    a = generate_runs(commits=40, seed=3, now=NOW)
    b = generate_runs(commits=40, seed=3, now=NOW)
    assert fingerprint(a) == fingerprint(b)


def test_history_stays_inside_the_30_day_scoring_window():
    runs = generate_runs(now=NOW)
    assert min(r.started_at for r in runs) >= NOW - timedelta(days=30)
    assert max(r.started_at for r in runs) <= NOW