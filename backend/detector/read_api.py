"""
Public, read-only API used by the dashboard.

Everything is scoped to a project slug and only works for projects marked
is_public=True. Private projects return 404 (not 403), so their existence
isn't revealed. Anonymous requests are rate limited (see REST_FRAMEWORK
settings).
"""
from datetime import timedelta

from django.db.models import Count, F, Max, Q
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .models import CaseResult, CIRun, ErrorGroup, Project, TrackedTest
from .services import SCORING_WINDOW_DAYS

FAIL_OUTCOMES = [CaseResult.Outcome.FAILED, CaseResult.Outcome.ERROR]


def get_public_project(slug: str) -> Project:
    return get_object_or_404(Project, slug=slug, is_public=True)


def window_start():
    return timezone.now() - timedelta(days=SCORING_WINDOW_DAYS)


class PublicReadMixin:
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]


class StandardPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class TrackedTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackedTest
        fields = [
            "id", "name", "status", "flakiness_score", "executions",
            "conflict_commits", "failure_rate", "flip_rate", "last_seen",
        ]


class TrackedTestListView(PublicReadMixin, ListAPIView):
    """GET /api/projects/<slug>/tests/?status=flaky,suspect&search=cart&page=1"""

    serializer_class = TrackedTestSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        project = get_public_project(self.kwargs["slug"])
        qs = TrackedTest.objects.filter(project=project)

        raw_status = self.request.query_params.get("status", "")
        wanted = [s for s in raw_status.split(",") if s in TrackedTest.Status.values]
        if wanted:
            qs = qs.filter(status__in=wanted)

        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)

        return qs.order_by(F("flakiness_score").desc(nulls_last=True), "name")


class TrackedTestDetailView(PublicReadMixin, APIView):
    """GET /api/projects/<slug>/tests/<id>/ : score, daily counts, recent runs, top errors"""

    def get(self, request, slug, test_id):
        project = get_public_project(slug)
        test = get_object_or_404(TrackedTest, pk=test_id, project=project)

        results = (
            CaseResult.objects
            .filter(test=test, executed_at__gte=window_start())
            .exclude(outcome=CaseResult.Outcome.SKIPPED)
        )

        daily = (
            results.annotate(day=TruncDate("executed_at"))
            .values("day")
            .annotate(runs=Count("id"), failures=Count("id", filter=Q(outcome__in=FAIL_OUTCOMES)))
            .order_by("day")
        )
        recent = results.select_related("run").order_by("-executed_at")[:50]
        errors = (
            results.filter(error_group__isnull=False)
            .values("error_group_id", "error_group__sample_message")
            .annotate(count=Count("id"), last_seen=Max("executed_at"))
            .order_by("-count")[:5]
        )

        return Response({
            "test": TrackedTestSerializer(test).data,
            "daily": [
                {"date": row["day"].isoformat(), "runs": row["runs"], "failures": row["failures"]}
                for row in daily
            ],
            "recent": [
                {
                    "executed_at": r.executed_at,
                    "outcome": r.outcome,
                    "commit": r.run.commit_sha[:7],
                    "branch": r.run.branch,
                    "attempt": r.run.run_attempt,
                    "duration_ms": r.duration_ms,
                }
                for r in recent
            ],
            "errors": [
                {
                    "group_id": row["error_group_id"],
                    "message": row["error_group__sample_message"][:300],
                    "count": row["count"],
                    "last_seen": row["last_seen"],
                }
                for row in errors
            ],
        })


class ErrorListView(PublicReadMixin, APIView):
    """GET /api/projects/<slug>/errors/ : most common failure messages"""

    def get(self, request, slug):
        project = get_public_project(slug)
        groups = (
            ErrorGroup.objects.filter(project=project)
            .annotate(tests_affected=Count("results__test", distinct=True))
            .order_by("-occurrences")[:20]
        )
        return Response([
            {
                "id": g.id,
                "message": g.sample_message[:300],
                "occurrences": g.occurrences,
                "tests_affected": g.tests_affected,
                "first_seen": g.first_seen,
                "last_seen": g.last_seen,
            }
            for g in groups
        ])


class StatsView(PublicReadMixin, APIView):
    """GET /api/projects/<slug>/stats/ : headline numbers for the dashboard"""

    def get(self, request, slug):
        project = get_public_project(slug)
        since = window_start()

        by_status = {value: 0 for value in TrackedTest.Status.values}
        for row in TrackedTest.objects.filter(project=project).values("status").annotate(n=Count("id")):
            by_status[row["status"]] = row["n"]

        runs = CIRun.objects.filter(project=project, started_at__gte=since)
        flaky_failures = CaseResult.objects.filter(
            run__project=project,
            executed_at__gte=since,
            test__status=TrackedTest.Status.FLAKY,
            outcome__in=FAIL_OUTCOMES,
        ).count()

        # Estimated CI time wasted: runs that contained a failure of a currently-flaky
        # test AND were followed by a later attempt on the same commit and job.
        latest_start = {}
        for sha, job, started in runs.values_list("commit_sha", "job_name", "started_at"):
            key = (sha, job)
            if key not in latest_start or started > latest_start[key]:
                latest_start[key] = started

        flaky_failed_runs = (
            runs.filter(
                results__test__status=TrackedTest.Status.FLAKY,
                results__outcome__in=FAIL_OUTCOMES,
            )
            .distinct()
            .values_list("id", "commit_sha", "job_name", "started_at", "duration_seconds")
        )
        wasted_runs, wasted_seconds = 0, 0.0
        for _id, sha, job, started, duration in flaky_failed_runs:
            if latest_start[(sha, job)] > started:
                wasted_runs += 1
                wasted_seconds += duration or 0.0

        return Response({
            "project": {"name": project.name, "slug": project.slug,
                        "default_branch": project.default_branch},
            "window_days": SCORING_WINDOW_DAYS,
            "tests": {"total": sum(by_status.values()), **by_status},
            "runs": {"total": runs.count(),
                    "commits": runs.values("commit_sha").distinct().count()},
            "flaky_failures": flaky_failures,
            "wasted_runs": wasted_runs,
            "wasted_ci_minutes": round(wasted_seconds / 60, 1),
        })