"""
Business logic for ingesting a parsed test report.

Kept separate from the HTTP layer so the same function can be reused by the
seed script and by management commands.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from .junit_parser import ERROR, FAILED, ParsedCase, ParsedReport
from .models import CaseResult, CIRun, ErrorGroup, Project, TrackedTest
from .scoring import Execution, compute_flakiness, error_fingerprint

SCORING_WINDOW_DAYS = 30

_SCORE_FIELDS = [
    "status", "flakiness_score", "executions", "conflict_commits",
    "failure_rate", "flip_rate", "score_computed_at",
]


@dataclass(frozen=True)
class RunMeta:
    run_id: str
    run_attempt: int
    job_name: str
    commit_sha: str
    branch: str
    pr_number: int | None
    started_at: datetime
    duration_seconds: float | None


@dataclass(frozen=True)
class IngestResult:
    run: CIRun
    created: bool            # False means this exact run was already uploaded
    tests_in_report: int
    tests_scored: int


def _fingerprint_for(case: ParsedCase) -> str | None:
    if case.outcome in (FAILED, ERROR) and case.error_message:
        return error_fingerprint(case.error_message)
    return None


def _get_or_create_tests(project: Project, report: ParsedReport) -> dict[str, TrackedTest]:
    names = [c.name for c in report.cases]
    existing = set(
        TrackedTest.objects.filter(project=project, name__in=names).values_list("name", flat=True)
    )
    TrackedTest.objects.bulk_create(
        [TrackedTest(project=project, name=c.name, file_path=c.file_path)
        for c in report.cases if c.name not in existing],
        ignore_conflicts=True,
    )
    return {t.name: t for t in TrackedTest.objects.filter(project=project, name__in=names)}


def _record_error_groups(project: Project, report: ParsedReport) -> dict[str, ErrorGroup]:
    counts: Counter[str] = Counter()
    samples: dict[str, str] = {}
    for case in report.cases:
        fp = _fingerprint_for(case)
        if fp:
            counts[fp] += 1
            samples.setdefault(fp, case.error_message)
    if not counts:
        return {}

    ErrorGroup.objects.bulk_create(
        [ErrorGroup(project=project, fingerprint=fp, sample_message=samples[fp]) for fp in counts],
        ignore_conflicts=True,
    )
    groups = {
        g.fingerprint: g
        for g in ErrorGroup.objects.filter(project=project, fingerprint__in=list(counts))
    }
    now = timezone.now()
    for fp, n in counts.items():
        # F() makes the increment happen in the database, so concurrent uploads don't lose counts.
        ErrorGroup.objects.filter(pk=groups[fp].pk).update(
            occurrences=F("occurrences") + n, last_seen=now
        )
    return groups


def refresh_scores(project: Project, tests: list[TrackedTest]) -> None:
    """Recompute and cache the flakiness score for the given tests."""
    since = timezone.now() - timedelta(days=SCORING_WINDOW_DAYS)
    rows = (
        CaseResult.objects
        .filter(test_id__in=[t.pk for t in tests], executed_at__gte=since)
        .exclude(outcome=CaseResult.Outcome.SKIPPED)
        .values_list("test_id", "run__commit_sha", "run__job_name",
                    "run__branch", "outcome", "executed_at")
    )
    by_test: dict[int, list[Execution]] = defaultdict(list)
    for test_id, sha, job, branch, outcome, executed_at in rows:
        by_test[test_id].append(
            Execution(
                commit_key=f"{sha}:{job}",
                passed=(outcome == CaseResult.Outcome.PASSED),
                executed_at=executed_at,
                on_default_branch=(branch == project.default_branch),
            )
        )

    now = timezone.now()
    for test in tests:
        result = compute_flakiness(by_test.get(test.pk, []))
        test.status = result.status
        test.flakiness_score = result.score
        test.executions = result.executions
        test.conflict_commits = result.conflict_commits
        test.failure_rate = result.failure_rate
        test.flip_rate = result.flip_rate
        test.score_computed_at = now
    TrackedTest.objects.bulk_update(tests, _SCORE_FIELDS, batch_size=500)


@transaction.atomic
def ingest_report(project: Project, meta: RunMeta, report: ParsedReport) -> IngestResult:
    duration = meta.duration_seconds if meta.duration_seconds is not None else report.total_seconds
    run, created = CIRun.objects.get_or_create(
        project=project,
        run_id=meta.run_id,
        run_attempt=meta.run_attempt,
        job_name=meta.job_name,
        defaults={
            "commit_sha": meta.commit_sha,
            "branch": meta.branch,
            "pr_number": meta.pr_number,
            "started_at": meta.started_at,
            "duration_seconds": duration,
        },
    )
    if not created:  # idempotent: same report uploaded again -> do nothing
        return IngestResult(run=run, created=False, tests_in_report=0, tests_scored=0)

    tests = _get_or_create_tests(project, report)
    groups = _record_error_groups(project, report)

    CaseResult.objects.bulk_create(
        [
            CaseResult(
                run=run,
                test=tests[case.name],
                outcome=case.outcome,
                duration_ms=case.duration_ms,
                error_group=groups.get(_fingerprint_for(case) or ""),
                error_message=case.error_message,
                executed_at=meta.started_at,
            )
            for case in report.cases
        ],
        batch_size=500,
    )

    TrackedTest.objects.filter(pk__in=[t.pk for t in tests.values()]).filter(
        Q(last_seen__isnull=True) | Q(last_seen__lt=meta.started_at)
    ).update(last_seen=meta.started_at)

    scored = list(tests.values())
    refresh_scores(project, scored)
    return IngestResult(run=run, created=True, tests_in_report=len(report.cases), tests_scored=len(scored))