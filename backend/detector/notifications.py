"""
Slack/email alerts for tests that just crossed into "flaky".

Design: this fires from inside refresh_scores() at ingest time, the moment a
test's cached status flips from something else to "flaky" — not from a
Celery task or a scheduled scan. Status only ever changes on ingest (see
services.refresh_scores), so there's nothing to gain from polling on a timer,
and this way the alert goes out within the same request that caused it.

The payload/body builders below are pure functions (no Django, no network),
so they're unit tested directly, the same way scoring.py and badge.py are.
Only send_slack_alert / send_email_alert touch the network, and they're the
only things a Django-level test needs to mock.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from urllib.request import Request, urlopen

logger = logging.getLogger("detector.notifications")


@dataclass(frozen=True)
class FlakyAlert:
    name: str
    score: float | None
    detail_url: str


def _line(a: FlakyAlert, linked: bool) -> str:
    label = f"<{a.detail_url}|`{a.name}`>" if linked else f"{a.name} ({a.detail_url})"
    return f"- {label} — score {a.score:.1f}" if a.score is not None else f"- {label}"


def build_slack_payload(project_name: str, dashboard_url: str, alerts: list[FlakyAlert]) -> dict:
    n = len(alerts)
    header = f":small_orange_diamond: *{n} test{'s' if n != 1 else ''} just went flaky* in *{project_name}*"
    lines = [_line(a, linked=True) for a in alerts]
    text = "\n".join([header, *lines, f"<{dashboard_url}|View dashboard>"])
    return {"text": text}


def build_email_subject(project_name: str, alerts: list[FlakyAlert]) -> str:
    n = len(alerts)
    return f"[flaky-detector] {n} new flaky test{'s' if n != 1 else ''} in {project_name}"


def build_email_body(project_name: str, dashboard_url: str, alerts: list[FlakyAlert]) -> str:
    n = len(alerts)
    lines = [_line(a, linked=False) for a in alerts]
    return "\n".join(
        [
            f"{n} test{'s' if n != 1 else ''} just crossed into 'flaky' in {project_name}:",
            "",
            *lines,
            "",
            f"View the dashboard: {dashboard_url}",
        ]
    )


def send_slack_alert(webhook_url: str, project_name: str, dashboard_url: str, alerts: list[FlakyAlert]) -> bool:
    """Best-effort: logs and returns False on any failure, never raises."""
    if not alerts:
        return True
    payload = build_slack_payload(project_name, dashboard_url, alerts)
    try:
        req = Request(
            webhook_url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req, timeout=5) as resp:
            ok = 200 <= resp.status < 300
            if not ok:
                logger.warning("Slack webhook returned status %s", resp.status)
            return ok
    except Exception:
        logger.exception("Failed to send Slack flaky alert")
        return False


def send_email_alert(recipient: str, project_name: str, dashboard_url: str, alerts: list[FlakyAlert]) -> bool:
    if not alerts:
        return True
    from django.core.mail import send_mail  # lazy import: keeps this module importable in pure unit tests

    try:
        send_mail(
            subject=build_email_subject(project_name, alerts),
            message=build_email_body(project_name, dashboard_url, alerts),
            from_email=None,  # falls back to settings.DEFAULT_FROM_EMAIL
            recipient_list=[recipient],
        )
        return True
    except Exception:
        logger.exception("Failed to send email flaky alert")
        return False


def notify_new_flaky_tests(project, dashboard_url: str, alerts: list[FlakyAlert]) -> None:
    """Fire-and-forget: sends to whichever channel(s) this project has configured."""
    if not alerts:
        return
    if getattr(project, "slack_webhook_url", ""):
        send_slack_alert(project.slack_webhook_url, project.name, dashboard_url, alerts)
    if getattr(project, "notify_email", ""):
        send_email_alert(project.notify_email, project.name, dashboard_url, alerts)