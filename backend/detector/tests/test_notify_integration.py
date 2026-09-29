"""
Django-level integration test: confirms the alert actually fires at the
right moment (edge-triggered) and only through channels the project
configured. The network/email calls are mocked — this suite must never
make a real HTTP request or send a real email.
"""
from unittest.mock import patch

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from detector.models import Project, TrackedTest

pytestmark = pytest.mark.django_db


def make_xml(failed: bool, message="assert 1 == 2"):
    body = f'<failure message="{message}">tb</failure>' if failed else ""
    xml = f'<testsuite><testcase classname="tests.demo" name="test_flaky" time="0.1">{body}</testcase></testsuite>'
    return xml.encode()


def upload(client, token, xml, **overrides):
    data = {
        "report": SimpleUploadedFile("r.xml", xml, content_type="application/xml"),
        "run_id": overrides.pop("run_id", "1"),
        "run_attempt": overrides.pop("run_attempt", "1"),
        "commit_sha": overrides.pop("commit_sha", "a" * 40),
        "branch": "main",
    }
    data.update(overrides)
    return client.post(reverse("ingest"), data, format="multipart", HTTP_AUTHORIZATION=f"Bearer {token}")

def push_conflicting_history(client, token, n_commits=6):
    """Six commits, each failing then passing on a same-commit re-run —
    real conflict evidence, enough to push a test's score into "flaky"."""
    for i in range(n_commits):
        sha = f"{i:040x}"
        upload(client, token, make_xml(failed=True), run_id=str(i), run_attempt="1", commit_sha=sha)
        upload(client, token, make_xml(failed=False), run_id=str(i), run_attempt="2", commit_sha=sha)

@patch("detector.notifications.urlopen")
def test_slack_alert_fires_when_a_test_first_turns_flaky(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value.status = 200
    project, token = Project.create_with_token(
        name="Shop", slug="shop-n1", default_branch="main", slack_webhook_url="https://hooks.slack.test/x"
    )
    client = APIClient()

    # Fail/pass on alternating commits until the scorer calls it flaky.
    push_conflicting_history(client, token)

    test = TrackedTest.objects.get(project=project)
    assert test.status == "flaky"
    assert mock_urlopen.called


@patch("detector.notifications.urlopen")
def test_no_slack_call_without_a_webhook_configured(mock_urlopen):
    project, token = Project.create_with_token(name="Shop", slug="shop-n2", default_branch="main")
    client = APIClient()
    push_conflicting_history(client, token)
    assert not mock_urlopen.called


@patch("detector.notifications.urlopen")
def test_no_repeat_alert_while_test_stays_flaky(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value.status = 200
    project, token = Project.create_with_token(
        name="Shop", slug="shop-n3", default_branch="main", slack_webhook_url="https://hooks.slack.test/x"
    )
    client = APIClient()
    push_conflicting_history(client, token)
    assert TrackedTest.objects.get(project=project).status == "flaky"
    calls_so_far = mock_urlopen.call_count
    assert calls_so_far >= 1

    # One more already-flaky run must not fire a second alert.
    upload(client, token, make_xml(failed=False), run_id="99", commit_sha="9" * 40)
    assert mock_urlopen.call_count == calls_so_far


def test_email_alert_fires_via_django_test_outbox():
    project, token = Project.create_with_token(
        name="Shop", slug="shop-n4", default_branch="main", notify_email="team@example.com"
    )
    client = APIClient()
    push_conflicting_history(client, token)

    assert TrackedTest.objects.get(project=project).status == "flaky"
    assert len(mail.outbox) == 1
    assert "shop-n4" in mail.outbox[0].subject.lower() or "Shop" in mail.outbox[0].subject
    assert "team@example.com" in mail.outbox[0].to


@patch("detector.notifications.urlopen", side_effect=OSError("network down"))
def test_slack_failure_never_breaks_ingestion(mock_urlopen):
    project, token = Project.create_with_token(
        name="Shop", slug="shop-n5", default_branch="main", slack_webhook_url="https://hooks.slack.test/x"
    )
    client = APIClient()
    resp = None
    for i in range(6):
        resp = upload(client, token, make_xml(failed=(i % 2 == 0)), run_id=str(i), commit_sha=f"{i:040x}")
    assert resp.status_code in (200, 201)  # ingest still succeeds even though the webhook call raised