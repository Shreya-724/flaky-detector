"""HTTP layer: token auth, request validation, and the ingest endpoint."""
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import serializers, status
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .junit_parser import JUnitParseError, parse_junit
from .models import Project
from .services import RunMeta, ingest_report

MAX_REPORT_BYTES = 5 * 1024 * 1024  # 5 MB


class ProjectTokenAuthentication(BaseAuthentication):
    """`Authorization: Bearer <project token>`. request.auth becomes the Project."""

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts or parts[0].lower() != b"bearer":
            return None  # no credentials -> DRF answers 401
        if len(parts) != 2:
            raise AuthenticationFailed("Invalid Authorization header.")
        try:
            raw_token = parts[1].decode()
        except UnicodeError:
            raise AuthenticationFailed("Invalid token.")
        try:
            project = Project.objects.get(token_hash=Project.hash_token(raw_token))
        except Project.DoesNotExist:
            raise AuthenticationFailed("Invalid token.")
        return (AnonymousUser(), project)

    def authenticate_header(self, request):
        return "Bearer"


class ProjectTokenScheme(OpenApiAuthenticationExtension):
    """Registers ProjectTokenAuthentication as its own named scheme in the
    OpenAPI docs, distinct from the JWT scheme used by /api/auth/. Without
    this, drf-spectacular would either warn or lump it in with JWT."""

    target_class = "detector.api.ProjectTokenAuthentication"
    name = "ProjectToken"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "Project token",
            "description": "The per-project CI upload token, shown once when the project is created "
                            "(or when its token is regenerated).",
        }


class HasProjectToken(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.auth, Project)


class IngestSerializer(serializers.Serializer):
    report = serializers.FileField(help_text="JUnit XML report, e.g. from `pytest --junitxml=report.xml`")
    run_id = serializers.CharField(max_length=64)
    run_attempt = serializers.IntegerField(min_value=1, default=1)
    job_name = serializers.CharField(max_length=100, allow_blank=True, default="")
    commit_sha = serializers.RegexField(r"^[0-9a-fA-F]{7,40}$")
    branch = serializers.CharField(max_length=200)
    pr_number = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    started_at = serializers.DateTimeField(required=False)
    duration_seconds = serializers.FloatField(min_value=0, required=False)

    def validate_report(self, value):
        if value.size > MAX_REPORT_BYTES:
            raise serializers.ValidationError("Report is larger than 5 MB.")
        return value


class IngestResponseSerializer(serializers.Serializer):
    run = serializers.IntegerField()
    created = serializers.BooleanField()
    tests_in_report = serializers.IntegerField()
    tests_scored = serializers.IntegerField()


@extend_schema(
    tags=["ingest"],
    summary="Upload a JUnit XML test report",
    description="Authenticate with `Authorization: Bearer <project token>`. Idempotent: uploading "
                "the same run_id/run_attempt/job_name again returns 200 instead of 201 and changes nothing.",
    request=IngestSerializer,
    responses={201: IngestResponseSerializer, 200: IngestResponseSerializer},
    examples=[
        OpenApiExample(
            "Created",
            value={"run": 42, "created": True, "tests_in_report": 13, "tests_scored": 13},
            response_only=True,
            status_codes=["201"],
        ),
    ],
)
class IngestView(APIView):
    """POST /api/ingest/  (multipart: report=<xml file> + run metadata)"""

    authentication_classes = [ProjectTokenAuthentication]
    permission_classes = [HasProjectToken]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = IngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            report = parse_junit(data["report"].read())
        except JUnitParseError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        meta = RunMeta(
            run_id=data["run_id"],
            run_attempt=data["run_attempt"],
            job_name=data["job_name"],
            commit_sha=data["commit_sha"].lower(),
            branch=data["branch"],
            pr_number=data.get("pr_number"),
            started_at=data.get("started_at") or timezone.now(),
            duration_seconds=data.get("duration_seconds"),
        )
        result = ingest_report(request.auth, meta, report)
        return Response(
            {
                "run": result.run.pk,
                "created": result.created,
                "tests_in_report": result.tests_in_report,
                "tests_scored": result.tests_scored,
            },
            status=status.HTTP_201_CREATED if result.created else status.HTTP_200_OK,
        )