import re

from detector.badge import COLOR_OK, COLOR_WARN, flaky_count_badge, render_badge_svg


def test_zero_flaky_is_green():
    svg = flaky_count_badge(0)
    assert COLOR_OK in svg
    assert COLOR_WARN not in svg
    assert ">0<" in svg


def test_nonzero_flaky_is_amber():
    svg = flaky_count_badge(4)
    assert COLOR_WARN in svg
    assert ">4<" in svg


def test_svg_is_well_formed_enough():
    svg = render_badge_svg("flaky tests", "4", COLOR_WARN)
    assert svg.startswith("<svg")
    assert svg.strip().endswith("</svg>")
    assert svg.count("<svg") == svg.count("</svg>")
    assert svg.count("<g") == svg.count("</g>")


def test_width_grows_with_longer_label():
    short = render_badge_svg("x", "1")
    long = render_badge_svg("a much longer label here", "1")

    def total_width(svg):
        return int(re.search(r'width="(\d+)"', svg).group(1))

    assert total_width(long) > total_width(short)


def test_aria_label_matches_content():
    svg = render_badge_svg("flaky tests", "4", COLOR_WARN)
    assert 'aria-label="flaky tests: 4"' in svg