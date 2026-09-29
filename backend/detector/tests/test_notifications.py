from detector.notifications import (
    FlakyAlert,
    build_email_body,
    build_email_subject,
    build_slack_payload,
)

ONE = [FlakyAlert(name="tests.a::test_x", score=77.8, detail_url="https://app/p/demo/tests/1")]
TWO = [
    FlakyAlert(name="tests.a::test_x", score=77.8, detail_url="https://app/p/demo/tests/1"),
    FlakyAlert(name="tests.b::test_y", score=None, detail_url="https://app/p/demo/tests/2"),
]


def test_slack_payload_singular_wording():
    payload = build_slack_payload("demo", "https://app/p/demo", ONE)
    assert "1 test just went flaky" in payload["text"]
    assert "tests.a::test_x" in payload["text"]
    assert "77.8" in payload["text"]
    assert "https://app/p/demo/tests/1" in payload["text"]
    assert "https://app/p/demo" in payload["text"]


def test_slack_payload_plural_wording_and_handles_missing_score():
    payload = build_slack_payload("demo", "https://app/p/demo", TWO)
    assert "2 tests just went flaky" in payload["text"]
    assert "tests.b::test_y" in payload["text"]
    assert "None" not in payload["text"]


def test_slack_payload_is_a_plain_text_dict():
    payload = build_slack_payload("demo", "https://app/p/demo", ONE)
    assert set(payload.keys()) == {"text"}
    assert isinstance(payload["text"], str)


def test_email_subject_counts_and_pluralizes():
    assert build_email_subject("demo", ONE) == "[flaky-detector] 1 new flaky test in demo"
    assert build_email_subject("demo", TWO) == "[flaky-detector] 2 new flaky tests in demo"


def test_email_body_lists_every_test_and_the_dashboard_link():
    body = build_email_body("demo", "https://app/p/demo", TWO)
    assert "tests.a::test_x" in body
    assert "tests.b::test_y" in body
    assert "https://app/p/demo" in body
    assert "None" not in body


def test_email_body_has_no_slack_markup():
    body = build_email_body("demo", "https://app/p/demo", ONE)
    assert "<" not in body
    assert "*" not in body