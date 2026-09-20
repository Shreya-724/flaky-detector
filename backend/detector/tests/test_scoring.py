import random
from datetime import datetime, timedelta

from detector.scoring import Execution, compute_flakiness, error_fingerprint

T0 = datetime(2026, 1, 1)


def simulate(fail_prob=0.0, broken_range=None, commits=60, retry_prob=0.7, seed=1):
    """Fake CI history on the default branch. A failed run is retried with retry_prob."""
    rng = random.Random(seed)
    out, t = [], 0
    for i in range(commits):
        attempts = 1
        while True:
            if broken_range and broken_range[0] <= i < broken_range[1]:
                failed = True
            else:
                failed = rng.random() < fail_prob
            out.append(Execution(f"sha{i}:test", not failed, T0 + timedelta(minutes=t), True))
            t += 1
            if failed and attempts < 3 and rng.random() < retry_prob:
                attempts += 1
                continue
            break
    return out


def test_stable_test_scores_zero():
    r = compute_flakiness(simulate(fail_prob=0.0))
    assert r.status == "stable" and r.score == 0


def test_always_failing_is_broken_not_flaky():
    r = compute_flakiness(simulate(fail_prob=1.0))
    assert r.status == "stable"
    assert r.conflict_commits == 0


def test_broken_then_fixed_is_not_flaky():
    r = compute_flakiness(simulate(broken_range=(20, 30)))
    assert r.status != "flaky"


def test_flaky_test_is_caught():
    r = compute_flakiness(simulate(fail_prob=0.2))
    assert r.status == "flaky", r


def test_mildly_flaky_is_at_least_suspect():
    r = compute_flakiness(simulate(fail_prob=0.05, commits=100))
    assert r.status in ("suspect", "flaky"), r


def test_too_little_data_is_not_judged():
    r = compute_flakiness(simulate(fail_prob=0.5, commits=3, retry_prob=0.0))
    assert r.status == "insufficient_data" and r.score is None


def test_single_conflict_with_few_runs_is_still_reported():
    ex = [Execution("a:j", False, T0, True), Execution("a:j", True, T0 + timedelta(minutes=1), True)]
    r = compute_flakiness(ex)
    assert r.conflict_commits == 1 and r.score is not None and r.score > 0


def test_fingerprint_groups_similar_errors():
    a = "TimeoutError: waited 5023ms for element at 0x7f3a9c on /app/tests/test_ui.py:88"
    b = "TimeoutError: waited 4987ms for element at 0x7f9b21 on /app/tests/test_ui.py:91"
    c = "AssertionError: expected 3 got 4"
    assert error_fingerprint(a) == error_fingerprint(b)
    assert error_fingerprint(a) != error_fingerprint(c)
