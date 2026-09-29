import io
import json
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flaky_detector_cli.cli import (
    build_parser,
    detect_branch,
    detect_commit_sha,
    detect_run_attempt,
    detect_run_id,
    encode_multipart,
    main,
    submit_report,
)


def test_encode_multipart_contains_all_fields_and_file_content(tmp_path=None):
    tmp = Path(tempfile.mkdtemp())
    report = tmp / "report.xml"
    report.write_text("<testsuite></testsuite>")

    body, content_type = encode_multipart(
        {"run_id": "42", "branch": "main"}, "report", report
    )
    text = body.decode()

    assert content_type.startswith("multipart/form-data; boundary=")
    boundary = content_type.split("boundary=")[1]
    assert text.count(f"--{boundary}") == 4  # 2 field parts + 1 file part + 1 closing boundary
    assert text.strip().endswith(f"--{boundary}--")
    assert 'name="run_id"' in text and "\r\n42\r\n" in text
    assert 'name="branch"' in text and "\r\nmain\r\n" in text
    assert 'name="report"; filename="report.xml"' in text
    assert "<testsuite></testsuite>" in text


def test_detect_commit_sha_prefers_github_env():
    with patch.dict(os.environ, {"GITHUB_SHA": "deadbeef"}, clear=False):
        assert detect_commit_sha() == "deadbeef"


def test_detect_branch_prefers_github_env():
    with patch.dict(os.environ, {"GITHUB_REF_NAME": "main"}, clear=False):
        assert detect_branch() == "main"


def test_detect_branch_falls_back_to_git_in_a_real_repo():
    tmp = Path(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.name", "a"], cwd=tmp, check=True)
    (tmp / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp, check=True)

    env = {k: v for k, v in os.environ.items() if k != "GITHUB_REF_NAME"}
    cwd = os.getcwd()
    try:
        os.chdir(tmp)
        with patch.dict(os.environ, env, clear=True):
            branch = detect_branch()
            sha = detect_commit_sha()
    finally:
        os.chdir(cwd)
    assert branch in ("main", "master")  # depends on the machine's git default
    assert sha is not None and len(sha) == 40


def test_detect_run_id_falls_back_to_a_local_placeholder():
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_RUN_ID"}
    with patch.dict(os.environ, env, clear=True):
        assert detect_run_id().startswith("local-")


def test_detect_run_attempt_defaults_to_one():
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_RUN_ATTEMPT"}
    with patch.dict(os.environ, env, clear=True):
        assert detect_run_attempt() == "1"


def test_submit_report_raises_on_missing_file():
    try:
        submit_report(
            url="https://x", token="t", report_path=Path("/no/such/file.xml"),
            commit_sha="a", branch="main", run_id="1", run_attempt="1",
        )
        raise AssertionError("expected SubmitError")
    except Exception as e:
        assert "not found" in str(e)


def test_build_parser_requires_a_subcommand():
    parser = build_parser()
    try:
        parser.parse_args([])
        raise AssertionError("expected SystemExit")
    except SystemExit:
        pass


def test_main_errors_cleanly_with_no_token():
    tmp = Path(tempfile.mkdtemp())
    report = tmp / "r.xml"
    report.write_text("<testsuite></testsuite>")
    env = {k: v for k, v in os.environ.items() if k != "FLAKY_DETECTOR_TOKEN"}
    err = io.StringIO()
    with patch.dict(os.environ, env, clear=True), redirect_stderr(err):
        code = main(["submit", str(report), "--url", "https://x"])
    assert code == 2
    assert "token" in err.getvalue()


@patch("flaky_detector_cli.cli.urllib.request.urlopen")
def test_main_success_path_prints_summary(mock_urlopen):
    tmp = Path(tempfile.mkdtemp())
    report = tmp / "r.xml"
    report.write_text("<testsuite></testsuite>")

    response = MagicMock()
    response.read.return_value = json.dumps(
        {"run": 7, "created": True, "tests_in_report": 3, "tests_scored": 3}
    ).encode()
    mock_urlopen.return_value.__enter__.return_value = response

    out = io.StringIO()
    with redirect_stdout(out):
        code = main([
            "submit", str(report),
            "--url", "https://api.example.com",
            "--token", "sekret",
            "--commit", "a" * 40,
            "--branch", "main",
            "--run-id", "1",
        ])
    assert code == 0
    assert "Created run 7" in out.getvalue()
    assert "3 tests, 3 scored" in out.getvalue()

    sent_request = mock_urlopen.call_args[0][0]
    assert sent_request.full_url == "https://api.example.com/api/ingest/"
    assert sent_request.get_header("Authorization") == "Bearer sekret"