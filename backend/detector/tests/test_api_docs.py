import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def test_schema_endpoint_returns_a_valid_openapi_document(client):
    resp = client.get(reverse("schema"), {"format": "json"})
    assert resp.status_code == 200
    body = json.loads(resp.content)
    assert body["openapi"].startswith("3.")
    assert body["info"]["title"] == "flaky-detector API"


def test_schema_includes_key_endpoints(client):
    resp = client.get(reverse("schema"), {"format": "json"})
    body = json.loads(resp.content)
    paths = body["paths"]
    assert "/api/ingest/" in paths
    assert "/api/auth/register/" in paths
    assert any(p.startswith("/api/projects/") and "badge" in p for p in paths)


def test_swagger_ui_page_loads(client):
    resp = client.get(reverse("swagger-ui"))
    assert resp.status_code == 200
    assert b"swagger" in resp.content.lower()


def test_redoc_page_loads(client):
    resp = client.get(reverse("redoc"))
    assert resp.status_code == 200