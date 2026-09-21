import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from detector.models import CaseResult, CIRun, ErrorGroup, Project, TrackedTest

pytestmark = pytest.mark.django_db

TEST_NAME = "tests.test_cart::test_checkout"


def make_xml(failed=False, message="assert 1 == 2"):
    body = f'<failure message="{message}">tb</failure>' if failed else ""
    xml = (
        '<testsuite><testcase classname="tests.test_cart" name="test_checkout" time="0.1">'
        f"{body}</testcase></testsuite>"
    )
    return xml.encode()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def project_and_token():
    return Project.create_with_token(name="demo", slug="demo", default_branch="main")


def upload(client, token, xml, **overrides):
    data = {
        "report": SimpleUploadedFile("report.xml", xml, content_type="application/xml"),
        "run_id": "100",
        "run_attempt": "1",
        "commit_sha": "a" * 40,
        "branch": "main",
    }
    data.update(overrides)
    extra = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
    return client.post(reverse("ingest"), data, format="multipart", **extra)


def test_missing_token_is_401(client):
    assert upload(client, None, make_xml()).status_code == 401


def test_wrong_token_is_401(client, project_and_token):
    assert upload(client, "not-a-real-token", make_xml()).status_code == 401


def test_raw_token_is_not_stored(project_and_token):
    project, raw = project_and_token
    assert project.token_hash != raw


def test_valid_upload_creates_run_test_and_result(client, project_and_token):
    _, token = project_and_token
    resp = upload(client, token, make_xml(failed=True))
    assert resp.status_code == 201
    assert resp.json()["created"] is True
    assert CIRun.objects.count() == 1
    assert TrackedTest.objects.get().name == TEST_NAME
    assert CaseResult.objects.get().outcome == "failed"


def test_uploading_same_run_twice_is_idempotent(client, project_and_token):
    _, token = project_and_token
    first = upload(client, token, make_xml())
    second = upload(client, token, make_xml())
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert CIRun.objects.count() == 1
    assert CaseResult.objects.count() == 1


def test_fail_then_pass_on_same_commit_is_detected_as_conflict(client, project_and_token):
    _, token = project_and_token
    upload(client, token, make_xml(failed=True), run_attempt="1")
    upload(client, token, make_xml(failed=False), run_attempt="2")
    test = TrackedTest.objects.get(name=TEST_NAME)
    assert test.executions == 2
    assert test.conflict_commits == 1
    assert test.status in ("suspect", "flaky")
    assert test.flakiness_score > 0


def test_similar_error_messages_share_one_error_group(client, project_and_token):
    _, token = project_and_token
    upload(client, token, make_xml(failed=True, message="Timeout after 5023ms"), run_id="1")
    upload(client, token, make_xml(failed=True, message="Timeout after 4987ms"), run_id="2")
    group = ErrorGroup.objects.get()
    assert group.occurrences == 2


def test_invalid_xml_is_400(client, project_and_token):
    _, token = project_and_token
    assert upload(client, token, b"not xml").status_code == 400


@pytest.mark.parametrize("bad_sha", ["", "zzzz", "abc"])
def test_bad_commit_sha_is_400(client, project_and_token, bad_sha):
    _, token = project_and_token
    assert upload(client, token, make_xml(), commit_sha=bad_sha).status_code == 400