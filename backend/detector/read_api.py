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
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .badge import flaky_count_badge
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
            "quarantined", "quarantined_at",
        ]


@extend_schema(tags=["tests"], summary="List a project's tests, ranked by flakiness score")
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


class DailyPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    runs = serializers.IntegerField()
    failures = serializers.IntegerField()


class RecentRunSerializer(serializers.Serializer):
    executed_at = serializers.DateTimeField()
    outcome = serializers.CharField()
    commit = serializers.CharField()
    branch = serializers.CharField()
    attempt = serializers.IntegerField()
    duration_ms = serializers.IntegerField(allow_null=True)


class TestErrorSerializer(serializers.Serializer):
    group_id = serializers.IntegerField()
    message = serializers.CharField()
    count = serializers.IntegerField()
    last_seen = serializers.DateTimeField()


class TestDetailSerializer(serializers.Serializer):
    """Shape of TrackedTestDetailView's response, for documentation only —
    the view builds this dict by hand rather than instantiating this class."""

    test = TrackedTestSerializer()
    daily = DailyPointSerializer(many=True)
    recent = RecentRunSerializer(many=True)
    errors = TestErrorSerializer(many=True)


@extend_schema(
    tags=["tests"],
    summary="One test's score, daily pass/fail counts, recent runs and top errors",
    responses=TestDetailSerializer,
)
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


class ErrorGroupSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    message = serializers.CharField()
    occurrences = serializers.IntegerField()
    tests_affected = serializers.IntegerField()
    first_seen = serializers.DateTimeField()
    last_seen = serializers.DateTimeField()


@extend_schema(tags=["errors"], summary="Most common failure messages, grouped by pattern", responses=ErrorGroupSerializer(many=True))
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


class ProjectSummarySerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.SlugField()
    default_branch = serializers.CharField()


class TestCountsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    flaky = serializers.IntegerField()
    suspect = serializers.IntegerField()
    stable = serializers.IntegerField()
    insufficient_data = serializers.IntegerField()


class RunCountsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    commits = serializers.IntegerField()


class FailureRateSerializer(serializers.Serializer):
    last_7d = serializers.FloatField(allow_null=True)
    prev_7d = serializers.FloatField(allow_null=True)
    delta_pp = serializers.FloatField(allow_null=True)


class StatsSerializer(serializers.Serializer):
    """Shape of StatsView's response, for documentation only."""

    project = ProjectSummarySerializer()
    window_days = serializers.IntegerField()
    tests = TestCountsSerializer()
    runs = RunCountsSerializer()
    flaky_failures = serializers.IntegerField()
    wasted_runs = serializers.IntegerField()
    wasted_ci_minutes = serializers.FloatField()
    failure_rate = FailureRateSerializer()


@extend_schema(tags=["stats"], summary="Headline numbers for the dashboard header", responses=StatsSerializer)
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

        now = timezone.now()
        executed = CaseResult.objects.filter(run__project=project).exclude(
            outcome=CaseResult.Outcome.SKIPPED
        )

        def fail_rate(qs):
            total = qs.count()
            if total == 0:
                return None
            return round(qs.filter(outcome__in=FAIL_OUTCOMES).count() * 100 / total, 2)

        last_7d = fail_rate(executed.filter(executed_at__gte=now - timedelta(days=7)))
        prev_7d = fail_rate(
            executed.filter(
                executed_at__gte=now - timedelta(days=14),
                executed_at__lt=now - timedelta(days=7),
            )
        )
        delta_pp = round(last_7d - prev_7d, 2) if last_7d is not None and prev_7d is not None else None

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
            "failure_rate": {"last_7d": last_7d, "prev_7d": prev_7d, "delta_pp": delta_pp},
        })


@extend_schema(
    tags=["badge"],
    summary="Embeddable SVG badge showing the current flaky-test count",
    description="Returns an SVG image (image/svg+xml), not JSON. Embed with "
                "`![flaky tests](.../badge.svg)` in a README.",
    responses={200: {"content": {"image/svg+xml": {"schema": {"type": "string"}}}}},
    examples=[OpenApiExample("4 flaky tests", value="<svg ...>...</svg>")],
)
class BadgeView(PublicReadMixin, APIView):
    """GET /api/projects/<slug>/badge.svg -> an embeddable "N flaky tests" badge."""

    def get(self, request, slug):
        project = get_public_project(slug)
        count = TrackedTest.objects.filter(project=project, status=TrackedTest.Status.FLAKY).count()
        svg = flaky_count_badge(count)
        response = HttpResponse(svg, content_type="image/svg+xml")
        response["Cache-Control"] = "max-age=300"
        return response