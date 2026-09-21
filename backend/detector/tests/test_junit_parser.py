import pytest

from detector.junit_parser import JUnitParseError, parse_junit

SAMPLE = b"""<?xml version="1.0" encoding="utf-8"?>
<testsuites>
<testsuite name="pytest" tests="4">
    <testcase classname="tests.test_cart" name="test_add" time="0.010"/>
    <testcase classname="tests.test_cart" name="test_checkout" time="0.250">
    <failure message="assert 1 == 2">Traceback (most recent call last): ...</failure>
    </testcase>
    <testcase classname="tests.test_cart" name="test_boom" time="0.005">
    <error message="RuntimeError: db down">trace</error>
    </testcase>
    <testcase classname="tests.test_cart" name="test_later" time="0.000">
    <skipped type="pytest.skip" message="not ready"/>
    </testcase>
</testsuite>
</testsuites>"""


def by_name(report):
    return {c.name: c for c in report.cases}


def test_parses_all_four_outcomes():
    cases = by_name(parse_junit(SAMPLE))
    assert cases["tests.test_cart::test_add"].outcome == "passed"
    assert cases["tests.test_cart::test_checkout"].outcome == "failed"
    assert cases["tests.test_cart::test_boom"].outcome == "error"
    assert cases["tests.test_cart::test_later"].outcome == "skipped"


def test_failure_message_and_duration():
    case = by_name(parse_junit(SAMPLE))["tests.test_cart::test_checkout"]
    assert case.error_message == "assert 1 == 2"
    assert case.duration_ms == 250


def test_total_seconds_is_sum_of_test_times():
    assert parse_junit(SAMPLE).total_seconds == pytest.approx(0.265)


def test_bare_testsuite_root_is_supported():
    xml = b'<testsuite><testcase classname="a" name="t" time="1"/></testsuite>'
    assert len(parse_junit(xml).cases) == 1


def test_duplicate_ids_keep_the_worst_outcome():
    xml = (b'<testsuite>'
        b'<testcase classname="a" name="t"/>'
        b'<testcase classname="a" name="t"><failure message="x"/></testcase>'
        b'</testsuite>')
    (case,) = parse_junit(xml).cases
    assert case.outcome == "failed"


def test_long_messages_are_truncated():
    xml = b'<testsuite><testcase name="t"><failure>' + b"x" * 5000 + b"</failure></testcase></testsuite>"
    assert len(parse_junit(xml).cases[0].error_message) == 2000


def test_invalid_xml_raises():
    with pytest.raises(JUnitParseError):
        parse_junit(b"this is not xml")


def test_empty_report_raises():
    with pytest.raises(JUnitParseError):
        parse_junit(b"<testsuites></testsuites>")


def test_entity_expansion_attack_is_rejected():
    bomb = (b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">'
            b'<!ENTITY b "&a;&a;&a;&a;">]><testsuite><testcase name="&b;"/></testsuite>')
    with pytest.raises(JUnitParseError):
        parse_junit(bomb)