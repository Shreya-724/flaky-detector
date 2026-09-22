from datetime import timedelta

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from detector.junit_parser import ParsedCase, ParsedReport
from detector.models import Project, TrackedTest
from detector.services import RunMeta, ingest_report

pytestmark = pytest.mark.django_db

FLAKY = "tests.shop::test_flaky_checkout"
STABLE = "tests.shop::test_stable_login"


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()  # anonymous rate limiting counts live in the cache


@pytest.fixture
def client():
    return APIClient()


def add_run(project, i, attempt, flaky_fails):
    """One CI run containing one flaky test and one stable test."""
    started = timezone.now() - timedelta(hours=12 - i) + timedelta(minutes=10 * (attempt - 1))
    cases = [
        ParsedCase(
            FLAKY,
            "failed" if flaky_fails else "passed",
            120,
            f"Timeout after {4000 + i}ms" if flaky_fails else "",
            "",
        ),
        ParsedCase(STABLE, "passed", 80, "", ""),
    ]
    meta = RunMeta(
        run_id=f"run-{i}", run_attempt=attempt, job_name="", commit_sha=f"{i:040x}",
        branch="main", pr_number=None, started_at=started, duration_seconds=300.0,
    )
    ingest_report(project, meta, ParsedReport(cases=cases, total_seconds=0.2))


@pytest.fixture
def project():
    """12 commits. The flaky test fails on even commits, then passes on the re-run."""
    proj, _ = Project.create_with_token(
        name="Shop", slug="shop", default_branch="main", is_public=True
    )
    for i in range(12):
        fails = i % 2 == 0
        add_run(proj, i, attempt=1, flaky_fails=fails)
        if fails:
            add_run(proj, i, attempt=2, flaky_fails=False)
    return proj


@pytest.mark.parametrize("route", ["project-stats", "project-tests", "project-errors"])
def test_private_project_is_404(client, route):
    Project.create_with_token(name="Secret", slug="secret", is_public=False)
    assert client.get(reverse(route, args=["secret"])).status_code == 404


def test_private_project_test_detail_is_404(client):
    private, _ = Project.create_with_token(name="Secret", slug="secret", is_public=False)
    test = TrackedTest.objects.create(project=private, name="t")
    assert client.get(reverse("test-detail", args=["secret", test.pk])).status_code == 404


def test_unknown_project_is_404(client):
    assert client.get(reverse("project-tests", args=["nope"])).status_code == 404


def test_test_list_is_sorted_by_score_and_needs_no_token(client, project):
    resp = client.get(reverse("project-tests", args=["shop"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    assert [t["name"] for t in body["results"]] == [FLAKY, STABLE]
    assert body["results"][0]["status"] == "flaky"


def test_status_filter(client, project):
    resp = client.get(reverse("project-tests", args=["shop"]), {"status": "flaky"})
    assert [t["name"] for t in resp.json()["results"]] == [FLAKY]


def test_search_filter(client, project):
    resp = client.get(reverse("project-tests", args=["shop"]), {"search": "login"})
    assert [t["name"] for t in resp.json()["results"]] == [STABLE]


def test_detail_returns_daily_recent_and_errors(client, project):
    test = TrackedTest.objects.get(project=project, name=FLAKY)
    body = client.get(reverse("test-detail", args=["shop", test.pk])).json()
    assert body["test"]["name"] == FLAKY
    assert sum(d["runs"] for d in body["daily"]) == 18
    assert sum(d["failures"] for d in body["daily"]) == 6
    assert len(body["recent"]) == 18
    assert body["errors"][0]["count"] == 6


def test_detail_of_a_test_from_another_project_is_404(client, project):
    other, _ = Project.create_with_token(name="Other", slug="other", is_public=True)
    foreign = TrackedTest.objects.create(project=other, name="x")
    assert client.get(reverse("test-detail", args=["shop", foreign.pk])).status_code == 404


def test_errors_endpoint_groups_similar_messages(client, project):
    body = client.get(reverse("project-errors", args=["shop"])).json()
    assert len(body) == 1
    assert body[0]["occurrences"] == 6
    assert body[0]["tests_affected"] == 1


def test_stats_counts_and_wasted_time(client, project):
    body = client.get(reverse("project-stats", args=["shop"])).json()
    assert body["tests"]["total"] == 2
    assert body["tests"]["flaky"] == 1
    assert body["tests"]["stable"] == 1
    assert body["flaky_failures"] == 6
    assert body["wasted_runs"] == 6
    assert body["wasted_ci_minutes"] == 30.0
    # 6 failures out of 36 executions, all within the last 7 days; nothing before that.
    assert body["failure_rate"] == {"last_7d": 16.67, "prev_7d": None, "delta_pp": None}