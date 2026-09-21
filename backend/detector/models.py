"""
Django models for the flaky test detector (app name: detector).

Relationships:
    Project 1--* CIRun 1--* CaseResult *--1 TrackedTest *--1 Project
    CaseResult *--0..1 ErrorGroup *--1 Project
"""
import hashlib
import secrets

from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    repo = models.CharField(max_length=200, blank=True, help_text="owner/repo")
    default_branch = models.CharField(max_length=100, default="main")
    is_public = models.BooleanField(default=False, help_text="Public projects can be read without a token.")
    # Store only a hash of the API token, like a password. Show the raw token once.
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @staticmethod
    def hash_token(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    @classmethod
    def create_with_token(cls, **kwargs):
        """Returns (project, raw_token). raw_token is never stored."""
        raw = secrets.token_urlsafe(32)
        project = cls.objects.create(token_hash=cls.hash_token(raw), **kwargs)
        return project, raw


class CIRun(models.Model):
    """One uploaded report: one job of one attempt of one workflow run."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="runs")
    run_id = models.CharField(max_length=64)               # GITHUB_RUN_ID
    run_attempt = models.PositiveSmallIntegerField(default=1)  # GITHUB_RUN_ATTEMPT
    job_name = models.CharField(max_length=100, blank=True)    # matrix/env, keeps conflicts honest
    commit_sha = models.CharField(max_length=40)
    branch = models.CharField(max_length=200)
    pr_number = models.PositiveIntegerField(null=True, blank=True)
    started_at = models.DateTimeField()
    duration_seconds = models.FloatField(null=True, blank=True)  # for "CI time wasted"
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # Idempotent ingestion: re-uploading the same report is a no-op.
            models.UniqueConstraint(
                fields=["project", "run_id", "run_attempt", "job_name"], name="uniq_ci_run"
            ),
        ]
        indexes = [
            models.Index(fields=["project", "commit_sha"]),
            models.Index(fields=["project", "started_at"]),
        ]

    @property
    def commit_key(self) -> str:
        return f"{self.commit_sha}:{self.job_name}"


class TrackedTest(models.Model):
    """A unique test in a project. Named TrackedTest, not Test, so pytest
    doesn't try to collect the model class as a test."""

    class Status(models.TextChoices):
        FLAKY = "flaky"
        SUSPECT = "suspect"
        STABLE = "stable"
        INSUFFICIENT = "insufficient_data"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tests")
    name = models.CharField(max_length=500)        # "tests/test_cart.py::test_checkout"
    file_path = models.CharField(max_length=300, blank=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    # Cached output of scoring.compute_flakiness(), refreshed after each ingest
    # (or by a management command). Keeps the dashboard list query cheap.
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INSUFFICIENT)
    flakiness_score = models.FloatField(null=True, blank=True)
    executions = models.PositiveIntegerField(default=0)
    conflict_commits = models.PositiveIntegerField(default=0)
    failure_rate = models.FloatField(default=0.0)
    flip_rate = models.FloatField(default=0.0)
    score_computed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "name"], name="uniq_test_per_project"),
        ]
        indexes = [
            models.Index(fields=["project", "-flakiness_score"]),
            models.Index(fields=["project", "status"]),
        ]

    def __str__(self):
        return self.name


class ErrorGroup(models.Model):
    """Failures whose normalized messages match share a fingerprint."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="error_groups")
    fingerprint = models.CharField(max_length=40)  # sha1 of normalize_error(message)
    sample_message = models.TextField()
    occurrences = models.PositiveIntegerField(default=0)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "fingerprint"], name="uniq_error_fp"),
        ]


class CaseResult(models.Model):
    """One test, in one CIRun. This table grows fastest, so keep rows small."""

    class Outcome(models.TextChoices):
        PASSED = "passed"
        FAILED = "failed"
        ERROR = "error"
        SKIPPED = "skipped"

    run = models.ForeignKey(CIRun, on_delete=models.CASCADE, related_name="results")
    test = models.ForeignKey(TrackedTest, on_delete=models.CASCADE, related_name="results")
    outcome = models.CharField(max_length=10, choices=Outcome.choices)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    error_group = models.ForeignKey(
        ErrorGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="results"
    )
    error_message = models.TextField(blank=True)   # truncate to ~2000 chars on ingest
    executed_at = models.DateTimeField()           # copied from run.started_at for fast range queries

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["run", "test"], name="uniq_result_per_run"),
        ]
        indexes = [
            models.Index(fields=["test", "executed_at"]),
            models.Index(fields=["test", "outcome"]),
        ]
