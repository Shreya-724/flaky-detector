import re

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from detector.models import Project, TrackedTest

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def register_and_auth(client, username="alice"):
    resp = client.post(
        reverse("auth-register"),
        {"username": username, "email": f"{username}@example.com", "password": "correct-horse-battery-staple"},
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.json()['access']}")
    return resp.json()


# ---- quarantine ---------------------------------------------------------------

def test_quarantine_requires_auth(client):
    project, _ = Project.create_with_token(name="Shop", slug="shop-q")
    test = TrackedTest.objects.create(project=project, name="t")
    resp = client.post(reverse("quarantine-test", args=["shop-q", test.pk]), {"quarantined": True})
    assert resp.status_code == 401


def test_owner_can_quarantine_and_unquarantine(client):
    register_and_auth(client)
    created = client.post(reverse("my-projects"), {"name": "Shop", "slug": "shop-q2"}).json()
    project = Project.objects.get(slug="shop-q2")
    test = TrackedTest.objects.create(project=project, name="tests.test_x::test_flaky", status="flaky")

    on = client.post(reverse("quarantine-test", args=["shop-q2", test.pk]), {"quarantined": True})
    assert on.status_code == 200
    body = on.json()
    assert body["quarantined"] is True
    assert body["quarantined_at"] is not None

    test.refresh_from_db()
    assert test.quarantined is True

    off = client.post(reverse("quarantine-test", args=["shop-q2", test.pk]), {"quarantined": False})
    assert off.json()["quarantined"] is False
    assert off.json()["quarantined_at"] is None


def test_cannot_quarantine_someone_elses_test(client):
    owner_client = APIClient()
    register_and_auth(owner_client, "owner")
    owner_client.post(reverse("my-projects"), {"name": "Shop", "slug": "shop-q3"})
    project = Project.objects.get(slug="shop-q3")
    test = TrackedTest.objects.create(project=project, name="t")

    register_and_auth(client, "someone_else")
    resp = client.post(reverse("quarantine-test", args=["shop-q3", test.pk]), {"quarantined": True})
    assert resp.status_code == 404
    test.refresh_from_db()
    assert test.quarantined is False


def test_quarantine_requires_boolean_body(client):
    register_and_auth(client)
    client.post(reverse("my-projects"), {"name": "Shop", "slug": "shop-q4"})
    project = Project.objects.get(slug="shop-q4")
    test = TrackedTest.objects.create(project=project, name="t")
    resp = client.post(reverse("quarantine-test", args=["shop-q4", test.pk]), {}, format="json")
    assert resp.status_code == 400


def test_public_read_api_exposes_quarantine_status(client):
    project, _ = Project.create_with_token(name="Shop", slug="shop-q5", is_public=True)
    TrackedTest.objects.create(project=project, name="t", quarantined=True)
    body = client.get(reverse("project-tests", args=["shop-q5"])).json()
    assert body["results"][0]["quarantined"] is True


# ---- badge ---------------------------------------------------------------------

def test_badge_is_svg_and_reflects_flaky_count(client):
    project, _ = Project.create_with_token(name="Shop", slug="shop-b", is_public=True)
    TrackedTest.objects.create(project=project, name="a", status="flaky")
    TrackedTest.objects.create(project=project, name="b", status="flaky")
    TrackedTest.objects.create(project=project, name="c", status="stable")

    resp = client.get(reverse("project-badge", args=["shop-b"]))
    assert resp.status_code == 200
    assert resp["Content-Type"] == "image/svg+xml"
    body = resp.content.decode()
    assert body.startswith("<svg")
    assert ">2<" in body  # 2 flaky tests, not the 1 stable one


def test_badge_is_404_for_private_project(client):
    Project.create_with_token(name="Secret", slug="secret-b", is_public=False)
    assert client.get(reverse("project-badge", args=["secret-b"])).status_code == 404


def test_badge_is_404_for_unknown_project(client):
    assert client.get(reverse("project-badge", args=["does-not-exist"])).status_code == 404