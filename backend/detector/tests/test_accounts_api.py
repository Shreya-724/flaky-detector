import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from detector.models import Project

pytestmark = pytest.mark.django_db
User = get_user_model()

VALID_PASSWORD = "correct-horse-battery-staple"  # long/uncommon enough to pass Django's validators


@pytest.fixture
def client():
    return APIClient()


def register(client, username="alice", email="alice@example.com", password=VALID_PASSWORD):
    return client.post(reverse("auth-register"), {"username": username, "email": email, "password": password})


def auth(client, token):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


# ---- registration / login ---------------------------------------------------

def test_register_creates_user_and_returns_tokens(client):
    resp = register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"
    assert "access" in body and "refresh" in body
    assert User.objects.filter(username="alice").exists()


def test_password_is_hashed_not_stored_raw(client):
    register(client)
    user = User.objects.get(username="alice")
    assert user.password != VALID_PASSWORD
    assert user.check_password(VALID_PASSWORD)


def test_duplicate_username_is_rejected(client):
    register(client)
    resp = register(client, email="someone-else@example.com")
    assert resp.status_code == 400


def test_duplicate_email_is_rejected(client):
    register(client)
    resp = register(client, username="alice2")
    assert resp.status_code == 400


def test_weak_password_is_rejected(client):
    resp = register(client, password="password")
    assert resp.status_code == 400


def test_login_returns_tokens(client):
    register(client)
    resp = client.post(reverse("auth-token"), {"username": "alice", "password": VALID_PASSWORD})
    assert resp.status_code == 200
    assert "access" in resp.json()


def test_login_with_wrong_password_is_401(client):
    register(client)
    resp = client.post(reverse("auth-token"), {"username": "alice", "password": "wrong"})
    assert resp.status_code == 401


def test_me_requires_auth(client):
    assert client.get(reverse("auth-me")).status_code == 401


def test_me_returns_current_user(client):
    token = register(client).json()["access"]
    auth(client, token)
    body = client.get(reverse("auth-me")).json()
    assert body == {"username": "alice", "email": "alice@example.com"}


# ---- project management ------------------------------------------------------

def test_create_project_requires_auth(client):
    resp = client.post(reverse("my-projects"), {"name": "Demo", "slug": "demo-x"})
    assert resp.status_code == 401


def test_create_project_returns_token_once_and_sets_owner(client):
    token = register(client).json()["access"]
    auth(client, token)
    resp = client.post(reverse("my-projects"), {"name": "Shop", "slug": "shop-x", "is_public": True})
    assert resp.status_code == 201
    body = resp.json()
    assert "token" in body and len(body["token"]) > 20
    assert "token" not in body["project"]
    project = Project.objects.get(slug="shop-x")
    assert project.owner.username == "alice"
    assert project.token_hash == Project.hash_token(body["token"])


def test_duplicate_slug_is_rejected(client):
    token = register(client).json()["access"]
    auth(client, token)
    client.post(reverse("my-projects"), {"name": "Shop", "slug": "shop-y"})
    resp = client.post(reverse("my-projects"), {"name": "Shop Again", "slug": "shop-y"})
    assert resp.status_code == 400


def test_list_projects_only_shows_own(client):
    alice_token = register(client, "alice", "alice@example.com").json()["access"]
    auth(client, alice_token)
    client.post(reverse("my-projects"), {"name": "Alice Co", "slug": "alice-co"})

    bob_client = APIClient()
    bob_token = register(bob_client, "bob", "bob@example.com").json()["access"]
    auth(bob_client, bob_token)
    bob_client.post(reverse("my-projects"), {"name": "Bob Co", "slug": "bob-co"})

    names = [p["name"] for p in client.get(reverse("my-projects")).json()]
    assert names == ["Alice Co"]


def test_project_detail_is_404_for_non_owner(client):
    alice_token = register(client, "alice", "alice@example.com").json()["access"]
    auth(client, alice_token)
    client.post(reverse("my-projects"), {"name": "Alice Co", "slug": "alice-co2"})

    bob_client = APIClient()
    bob_token = register(bob_client, "bob", "bob@example.com").json()["access"]
    auth(bob_client, bob_token)
    assert bob_client.get(reverse("my-project-detail", args=["alice-co2"])).status_code == 404


def test_patch_updates_allowed_fields_only(client):
    token = register(client).json()["access"]
    auth(client, token)
    client.post(reverse("my-projects"), {"name": "Shop", "slug": "shop-z"})
    resp = client.patch(
        reverse("my-project-detail", args=["shop-z"]),
        {"is_public": True, "default_branch": "trunk", "slug": "hacked"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    project = Project.objects.get(pk=resp.json()["id"])
    assert project.is_public is True
    assert project.default_branch == "trunk"
    assert project.slug == "shop-z"  # slug is not patchable


def test_regenerate_token_invalidates_the_old_one(client):
    token = register(client).json()["access"]
    auth(client, token)
    created = client.post(reverse("my-projects"), {"name": "Shop", "slug": "shop-r"}).json()
    old_token = created["token"]

    regen = client.post(reverse("my-project-regen-token", args=["shop-r"]))
    assert regen.status_code == 200
    new_token = regen.json()["token"]
    assert new_token != old_token

    xml = b'<testsuite><testcase name="t"/></testsuite>'
    ingest_data = {
        "report": SimpleUploadedFile("r.xml", xml, content_type="application/xml"),
        "run_id": "1",
        "commit_sha": "a" * 40,
        "branch": "main",
    }
    old_client = APIClient()
    resp_old = old_client.post(
        reverse("ingest"), ingest_data, format="multipart", HTTP_AUTHORIZATION=f"Bearer {old_token}"
    )
    assert resp_old.status_code == 401

    ingest_data["report"] = SimpleUploadedFile("r.xml", xml, content_type="application/xml")
    new_client = APIClient()
    resp_new = new_client.post(
        reverse("ingest"), ingest_data, format="multipart", HTTP_AUTHORIZATION=f"Bearer {new_token}"
    )
    assert resp_new.status_code == 201