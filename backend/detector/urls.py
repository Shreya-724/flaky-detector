from django.urls import path

from .api import IngestView
from .read_api import ErrorListView, StatsView, TrackedTestDetailView, TrackedTestListView

urlpatterns = [
    path("ingest/", IngestView.as_view(), name="ingest"),
    path("projects/<slug:slug>/stats/", StatsView.as_view(), name="project-stats"),
    path("projects/<slug:slug>/tests/", TrackedTestListView.as_view(), name="project-tests"),
    path("projects/<slug:slug>/tests/<int:test_id>/", TrackedTestDetailView.as_view(), name="test-detail"),
    path("projects/<slug:slug>/errors/", ErrorListView.as_view(), name="project-errors"),
]