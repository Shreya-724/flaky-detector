"""
flaky-detector-cli: a tiny, zero-dependency command that uploads a JUnit XML
report to a flaky-detector project.

    flaky-detector submit report.xml

Reads FLAKY_DETECTOR_URL and FLAKY_DETECTOR_TOKEN from the environment by
default (the same two names your GitHub Actions workflow secret/variable
already use), or pass --url/--token explicitly. Everything else (commit sha,
branch, run id/attempt) is auto-detected: from GitHub Actions' own env vars
when running in CI, falling back to your local `git` checkout otherwise.

No third-party dependencies: just the standard library.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from . import __version__

DEFAULT_TIMEOUT = 30


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=5, check=True
        )
        value = out.stdout.strip()
        return value or None
    except Exception:
        return None


def detect_commit_sha() -> str | None:
    return os.environ.get("GITHUB_SHA") or _git("rev-parse", "HEAD")


def detect_branch() -> str | None:
    ref = os.environ.get("GITHUB_REF_NAME")
    if ref:
        return ref
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    return None if branch == "HEAD" else branch  # "HEAD" means a detached checkout, not a real branch


def detect_run_id() -> str:
    return os.environ.get("GITHUB_RUN_ID") or f"local-{int(time.time())}"


def detect_run_attempt() -> str:
    return os.environ.get("GITHUB_RUN_ATTEMPT") or "1"


def encode_multipart(fields: dict[str, str], file_field: str, file_path: Path) -> tuple[bytes, str]:
    """Hand-rolled multipart/form-data body (stdlib only, no `requests`)."""
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []

    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )

    content_type = mimetypes.guess_type(file_path.name)[0] or "application/xml"
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
            f'filename="{file_path.name}"\r\nContent-Type: {content_type}\r\n\r\n'
        ).encode()
        + file_path.read_bytes()
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())

    body = b"".join(parts)
    return body, f"multipart/form-data; boundary={boundary}"


class SubmitError(RuntimeError):
    pass


def submit_report(
    *,
    url: str,
    token: str,
    report_path: Path,
    commit_sha: str,
    branch: str,
    run_id: str,
    run_attempt: str,
    job_name: str = "",
) -> dict:
    if not report_path.exists():
        raise SubmitError(f"Report file not found: {report_path}")

    fields = {
        "run_id": run_id,
        "run_attempt": run_attempt,
        "job_name": job_name,
        "commit_sha": commit_sha,
        "branch": branch,
    }
    body, content_type = encode_multipart(fields, "report", report_path)

    request = urllib.request.Request(
        url.rstrip("/") + "/api/ingest/",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": content_type,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise SubmitError(f"Server rejected the upload ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise SubmitError(f"Could not reach {url}: {exc.reason}") from exc
    except OSError as exc:
        raise SubmitError(f"Connection to {url} failed: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flaky-detector", description=__doc__.split("\n\n")[0])
    parser.add_argument("--version", action="version", version=f"flaky-detector-cli {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    submit = sub.add_parser("submit", help="Upload a JUnit XML report")
    submit.add_argument("report", type=Path, help="Path to the JUnit XML report, e.g. report.xml")
    submit.add_argument("--url", default=os.environ.get("FLAKY_DETECTOR_URL"),
                        help="Backend base URL (env: FLAKY_DETECTOR_URL)")
    submit.add_argument("--token", default=os.environ.get("FLAKY_DETECTOR_TOKEN"),
                        help="Project upload token (env: FLAKY_DETECTOR_TOKEN)")
    submit.add_argument("--commit", default=None, help="Commit SHA (auto-detected if omitted)")
    submit.add_argument("--branch", default=None, help="Branch name (auto-detected if omitted)")
    submit.add_argument("--run-id", default=None, help="CI run id (auto-detected if omitted)")
    submit.add_argument("--run-attempt", default=None, help="CI run attempt (auto-detected if omitted)")
    submit.add_argument("--job-name", default="", help="Job name, for matrix builds")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "submit":
        if not args.url:
            print("error: no backend URL given (pass --url or set FLAKY_DETECTOR_URL)", file=sys.stderr)
            return 2
        if not args.token:
            print("error: no token given (pass --token or set FLAKY_DETECTOR_TOKEN)", file=sys.stderr)
            return 2

        commit_sha = args.commit or detect_commit_sha()
        branch = args.branch or detect_branch()
        if not commit_sha:
            print("error: could not determine commit SHA (pass --commit)", file=sys.stderr)
            return 2
        if not branch:
            print("error: could not determine branch (pass --branch)", file=sys.stderr)
            return 2

        try:
            result = submit_report(
                url=args.url,
                token=args.token,
                report_path=args.report,
                commit_sha=commit_sha,
                branch=branch,
                run_id=args.run_id or detect_run_id(),
                run_attempt=args.run_attempt or detect_run_attempt(),
                job_name=args.job_name,
            )
        except SubmitError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        verb = "Created" if result.get("created") else "Already recorded"
        print(f"{verb} run {result.get('run')}: "
              f"{result.get('tests_in_report', 0)} tests, {result.get('tests_scored', 0)} scored.")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())