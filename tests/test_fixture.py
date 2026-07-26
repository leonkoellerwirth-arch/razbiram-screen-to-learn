"""The synthetic fixture must be consumable by the pipeline, not merely present.

These tests parse the committed fixture with the standard library and run it through the real
identity module. They need no browser, so they belong in the offline gate; the Playwright layer
that drives the live DOM transitions comes with P5.6.
"""

from __future__ import annotations

import random
from html.parser import HTMLParser
from pathlib import Path

import pytest

from razbiram_screen_to_learn.identity import question_fingerprint

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "pages"
FIXTURE_HTML = FIXTURE_DIR / "fixture.html"

EXPECTED_FAMILIES = {
    "single-choice",
    "multiple-select",
    "true-false",
    "flashcard",
    "image-occlusion",
}


class _QuestionParser(HTMLParser):
    """Collect question containers, their family, and their option cleanText values."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.questions: dict[str, dict] = {}
        self._current: str | None = None
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        question_id = attributes.get("data-question-id")
        if question_id and attributes.get("data-family"):
            self._current = question_id
            self._depth = 0
            self.questions[question_id] = {
                "family": attributes["data-family"],
                "options": [],
            }
            return
        if self._current is None:
            return
        self._depth += 1
        clean = attributes.get("data-clean-text")
        if clean:
            self.questions[self._current]["options"].append(clean)

    def handle_endtag(self, tag: str) -> None:
        if self._current is not None and tag == "section":
            self._current = None


@pytest.fixture(scope="module")
def parsed() -> dict[str, dict]:
    parser = _QuestionParser()
    parser.feed(FIXTURE_HTML.read_text(encoding="utf-8"))
    return parser.questions


def test_fixture_exists_and_is_self_contained() -> None:
    """Golden runs must work offline; a remote asset would make the corpus non-deterministic."""
    assert FIXTURE_HTML.exists()
    text = FIXTURE_HTML.read_text(encoding="utf-8")
    for marker in ("http://", "https://"):
        for line in text.splitlines():
            if marker in line:
                assert "www.w3.org/2000/svg" in line, f"external reference: {line.strip()}"


def test_every_card_family_is_represented(parsed: dict[str, dict]) -> None:
    assert {q["family"] for q in parsed.values()} == EXPECTED_FAMILIES


def test_option_bearing_families_expose_clean_text(parsed: dict[str, dict]) -> None:
    """cleanText is what the fingerprint hashes; without it the extractor has nothing stable."""
    for question_id, question in parsed.items():
        if question["family"] in {"single-choice", "multiple-select", "true-false"}:
            assert question["options"], f"{question_id} exposes no data-clean-text options"


def test_fingerprint_survives_option_reordering(parsed: dict[str, dict]) -> None:
    """Golden case G13, end to end: fixture DOM through the real identity module."""
    single = next(q for q in parsed.values() if q["family"] == "single-choice")
    options = single["options"]
    assert len(options) >= 3

    def fingerprint(order: list[str]) -> str:
        return question_fingerprint(
            origin="https://fixture.local",
            path="/fixture.html",
            card_family="single-choice",
            question_text="Through which medium does light travel fastest?",
            option_texts=order,
        )

    baseline = fingerprint(options)
    shuffled = list(options)
    rng = random.Random(13)
    for _ in range(10):
        rng.shuffle(shuffled)
        assert fingerprint(shuffled) == baseline


def test_reveal_feedback_marker_does_not_change_the_fingerprint(parsed: dict[str, dict]) -> None:
    """The fixture prepends "✓ " in the reveal state; cleanText must absorb it."""
    single = next(q for q in parsed.values() if q["family"] == "single-choice")

    def fingerprint(order: list[str]) -> str:
        return question_fingerprint(
            origin="https://fixture.local",
            path="/fixture.html",
            card_family="single-choice",
            question_text="Through which medium does light travel fastest?",
            option_texts=order,
        )

    revealed = ["✓ " + single["options"][0], *single["options"][1:]]
    assert fingerprint(revealed) == fingerprint(single["options"])


def test_native_inputs_do_not_carry_aria_checked() -> None:
    """ARIA in HTML prohibits aria-checked on native radio/checkbox inputs.

    The fixture is the reference for DOM-first extraction: if it modelled the state with a
    prohibited attribute, extractors would learn to read the wrong thing and would then fail on
    real pages that correctly use only the native checked property.
    """
    script = (FIXTURE_DIR / "fixture.js").read_text(encoding="utf-8")
    offending = [
        line
        for line in script.splitlines()
        if "aria-checked" in line and not line.strip().startswith("//")
    ]
    assert not offending, f"aria-checked set on native inputs: {offending}"
