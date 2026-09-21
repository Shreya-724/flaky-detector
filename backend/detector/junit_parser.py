"""
Parse a JUnit XML report (what `pytest --junitxml=report.xml` produces) into
plain Python objects. No Django imports, so it is easy to unit test.

defusedxml is used instead of the standard library parser because this will
parse files uploaded by strangers, and the stdlib parser can be abused with
"billion laughs" style entity-expansion attacks.
"""
from __future__ import annotations

from dataclasses import dataclass

from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

MAX_MESSAGE_CHARS = 2000

PASSED, FAILED, ERROR, SKIPPED = "passed", "failed", "error", "skipped"

# If the same test id appears twice in one report, keep the "worst" outcome.
_SEVERITY = {ERROR: 3, FAILED: 2, PASSED: 1, SKIPPED: 0}


class JUnitParseError(ValueError):
    """Raised when the report is not valid or contains no test cases."""


@dataclass(frozen=True)
class ParsedCase:
    name: str                 # "tests.test_cart::test_checkout"
    outcome: str              # passed | failed | error | skipped
    duration_ms: int | None
    error_message: str        # empty unless failed/error
    file_path: str            # empty if the report doesn't include it


@dataclass(frozen=True)
class ParsedReport:
    cases: list[ParsedCase]
    total_seconds: float      # sum of test durations (a rough job-time proxy)


def _outcome_and_message(testcase) -> tuple[str, str]:
    for tag, outcome in (("error", ERROR), ("failure", FAILED), ("skipped", SKIPPED)):
        child = testcase.find(tag)
        if child is not None:
            message = child.get("message") or (child.text or "")
            return outcome, message.strip()[:MAX_MESSAGE_CHARS]
    return PASSED, ""


def parse_junit(xml_bytes: bytes) -> ParsedReport:
    try:
        root = ET.fromstring(xml_bytes)
    except (ET.ParseError, DefusedXmlException) as exc:
        raise JUnitParseError(f"Invalid or unsafe XML: {exc}") from exc

    by_name: dict[str, ParsedCase] = {}
    total_seconds = 0.0

    # iter() handles both <testsuites><testsuite>... and a bare <testsuite> root.
    for tc in root.iter("testcase"):
        test_name = tc.get("name")
        if not test_name:
            continue
        classname = tc.get("classname") or ""
        full_name = f"{classname}::{test_name}" if classname else test_name

        try:
            seconds = float(tc.get("time") or 0)
        except ValueError:
            seconds = 0.0
        total_seconds += seconds

        outcome, message = _outcome_and_message(tc)
        case = ParsedCase(
            name=full_name[:500],
            outcome=outcome,
            duration_ms=int(seconds * 1000),
            error_message=message,
            file_path=(tc.get("file") or "")[:300],
        )
        existing = by_name.get(case.name)
        if existing is None or _SEVERITY[case.outcome] > _SEVERITY[existing.outcome]:
            by_name[case.name] = case

    if not by_name:
        raise JUnitParseError("No test cases found in report.")
    return ParsedReport(cases=list(by_name.values()), total_seconds=round(total_seconds, 3))