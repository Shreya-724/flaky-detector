"""
python manage.py seed_demo [--commits 150] [--seed 42] [--reset]

Fills the database with fake CI history by pushing it through the real ingest
pipeline (ingest_report), so it doubles as a load test of that code path.
"""
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.models import F

from detector.junit_parser import ParsedReport
from detector.models import Project, TrackedTest
from detector.seed_data import generate_runs
from detector.services import RunMeta, ingest_report

SLUG = "demo-seed"


class Command(BaseCommand):
    help = "Fill the database with fake CI history for demos and screenshots."

    def add_arguments(self, parser):
        parser.add_argument("--commits", type=int, default=150)
        parser.add_argument("--seed", type=int, default=42, help="Same seed = same history")
        parser.add_argument("--reset", action="store_true",
                            help="Delete the existing demo project (and its data) first")

    def handle(self, *args, **opts):
        if opts["reset"]:
            Project.objects.filter(slug=SLUG).delete()

        project = Project.objects.filter(slug=SLUG).first()
        if project is None:
            # The seed goes through ingest_report directly, so the token is not needed.
            project, _token = Project.create_with_token(
                name="Demo (seeded)", slug=SLUG, default_branch="main", is_public=True
            )

        runs = generate_runs(commits=opts["commits"], seed=opts["seed"])
        self.stdout.write(f"Ingesting {len(runs)} runs (this can take a little while)...")

        created = 0
        for run in runs:
            meta = RunMeta(
                run_id=run.run_id,
                run_attempt=run.run_attempt,
                job_name="",
                commit_sha=run.commit_sha,
                branch=run.branch,
                pr_number=None,
                started_at=run.started_at,
                duration_seconds=240 + int(run.commit_sha[:4], 16) % 180,
            )
            report = ParsedReport(
                cases=run.cases,
                total_seconds=sum(c.duration_ms or 0 for c in run.cases) / 1000,
            )
            created += ingest_report(project, meta, report).created

        tests = TrackedTest.objects.filter(project=project)
        counts = Counter(tests.values_list("status", flat=True))
        self.stdout.write(self.style.SUCCESS(
            f"Done: {created} new runs. Statuses: {dict(counts)}"
        ))
        self.stdout.write("Top of the leaderboard:")
        top = tests.order_by(F("flakiness_score").desc(nulls_last=True))[:6]
        for t in top:
            self.stdout.write(
                f"  {t.flakiness_score!s:>5}  {t.status:<9} conflicts={t.conflict_commits:<3} {t.name}"
            )