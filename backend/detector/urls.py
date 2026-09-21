from django.urls import path

from .api import IngestView

urlpatterns = [
    path("ingest/", IngestView.as_view(), name="ingest"),
]