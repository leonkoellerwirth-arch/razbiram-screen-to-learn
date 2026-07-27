"""The third reading of a page, and the score that decides when it wins.

Written from one measured failure. On ``fixtures/images/quiz.png`` tesseract drops the leading
digit of question 2, so the metals question inherits its neighbour's number and binds the key row
belonging to the true/false question — exporting "Iron" alone where the page prints "A, C". Both
readings find three answerable questions, so counting them cannot tell the two apart. What tells
them apart is that one reading has two questions claiming the same printed number.

Nothing here needs ollama: the reader's contract is that its absence costs nothing but itself,
and that is the first thing tested.
"""

from __future__ import annotations

from dataclasses import replace
from itertools import pairwise

from razbiram_screen_to_learn import vision
from razbiram_screen_to_learn.pipeline import (
    collided_indices,
    marks_correctness,
    process_text,
    reading_score,
)
from razbiram_screen_to_learn.textcards import positional_marker
from razbiram_screen_to_learn.textseg import segment

#: ``fixtures/images/quiz.png`` exactly as tesseract reads it. Pinned verbatim rather than written
#: by hand: an invented approximation of a lost digit does not segment the way the real one does,
#: and it was the real one that shipped a wrong answer.
LOST_DIGIT = """\
Biology — practice test

1.

Which organ produces insulin?
A) Liver

B) Pancreas

C) Kidney

D) Spleen

. Select all that apply. Which of these are metals?

A) Iron

B) Oxygen
C) Copper
D) Helium

3. A photon has zero rest mass.

A) True
B) False

Answers:

1.

B

2.A,C
3.A
"""

#: The same page as ``glm-ocr`` reads it: same questions, numbering intact.
INTACT = """\
Biology — practice test

1. Which organ produces insulin?
   A) Liver
   B) Pancreas
   C) Kidney
   D) Spleen

2. Select all that apply. Which of these are metals?
   A) Iron
   B) Oxygen
   C) Copper
   D) Helium

3. A photon has zero rest mass.
   A) True
   B) False

Answers:
1. B
2. A, C
3. A
"""


class TestCollidedIndices:
    def test_a_clean_reading_has_no_collisions(self) -> None:
        blocks, _ = segment(INTACT)
        assert collided_indices(blocks) == 0

    def test_a_lost_digit_makes_two_questions_claim_one_number(self) -> None:
        blocks, _ = segment(LOST_DIGIT)
        assert collided_indices(blocks) > 0

    def test_an_unanswerable_block_never_collides(self) -> None:
        """The title carries no options, so it cannot bind a key and must not count against.

        It shares its number with question 1 in both readings; only answerable blocks are judged.
        """
        blocks, _ = segment(INTACT)
        assert [block.index for block in blocks][:2] == [1, 1]
        assert collided_indices(blocks) == 0


class TestWhatACollisionCosts:
    """Why the collision count is worth measuring: it is what a wrong answer looks like upstream."""

    def _metals_answers(self, text: str) -> list[str]:
        result = process_text(text)
        card = next(c for c in result.document.cards if c.family == "multiple-select")
        return [option.text for option in (card.options or []) if option.isCorrect]

    def test_the_damaged_reading_binds_the_wrong_key_row(self) -> None:
        """The page prints "2. A, C". Losing the digit exports Iron alone — silently, unblocked."""
        assert self._metals_answers(LOST_DIGIT) == ["Iron"]

    def test_the_intact_reading_binds_what_the_page_printed(self) -> None:
        assert self._metals_answers(INTACT) == ["Iron", "Copper"]


class TestReadingScore:
    def test_finding_more_questions_wins_outright(self) -> None:
        """A card nobody extracted cannot be reviewed, so coverage outranks tidiness."""
        fewer, _ = segment("1. Only question?\nA) Yes\nB) No\n")
        more, _ = segment(LOST_DIGIT)
        assert reading_score(more) > reading_score(fewer)

    def test_between_equal_readings_intact_numbering_wins(self) -> None:
        intact, _ = segment(INTACT)
        damaged, _ = segment(LOST_DIGIT)
        assert reading_score(intact)[0] == reading_score(damaged)[0]
        assert reading_score(intact) > reading_score(damaged)


class TestAPageThatMarksItsOwnAnswers:
    """A transcript is text; a tint is not. The reading holding the answers is not displaced."""

    def test_an_unmarked_reading_leaves_the_model_free_to_run(self) -> None:
        blocks, _ = segment(INTACT)
        assert not marks_correctness(blocks)

    def test_a_marked_reading_is_not_displaced(self) -> None:
        blocks, _ = segment(INTACT)
        marked = [
            replace(
                block,
                option_lines=[replace(line, marked=True) for line in block.option_lines[:1]]
                + list(block.option_lines[1:]),
            )
            for block in blocks
        ]
        assert marks_correctness(marked)


class TestManyOptionsDoNotCrashTheUpload:
    def test_a_block_longer_than_the_alphabet_still_builds(self) -> None:
        """Observed on a transcript whose bullet lines ran together into one block of thirty.

        The reader raised IndexError, which loses every other question in the same upload — the
        one failure shape a local tool must not have.
        """
        options = "\n".join(f"- Option number {n}" for n in range(30))
        result = process_text(f"1. A question with far too many options?\n{options}\n")
        assert result.document.cards or result.export.blocked

    def test_no_option_past_the_alphabet_is_mistaken_for_a_key_letter(self) -> None:
        assert positional_marker(0) == "A"
        assert positional_marker(25) == "Z"
        assert positional_marker(26) == ""


class TestBanding:
    """A scroll is cut into page-sized bands; a page is left alone."""

    def _image(self, width: int, height: int):
        from PIL import Image

        return Image.new("RGB", (width, height), "white")

    def test_a_page_sized_capture_is_one_band(self) -> None:
        assert vision.band_bounds(self._image(2400, 1638)) == [(0, 1638)]

    def test_a_wide_capture_is_never_banded(self) -> None:
        """Height alone is not the signal — a poster is not a scroll."""
        assert vision.band_bounds(self._image(4000, 2600)) == [(0, 2600)]

    def test_a_scroll_is_cut_into_page_sized_bands(self) -> None:
        bounds = vision.band_bounds(self._image(2500, 28662))
        assert len(bounds) > 10
        assert bounds[0][0] == 0
        assert bounds[-1][1] == 28662

    def test_the_bands_cover_the_capture_exactly_once(self) -> None:
        """No overlap and no gap: text transcribed twice is text something must later dedupe."""
        bounds = vision.band_bounds(self._image(2500, 28662))
        for (_, previous_bottom), (top, _) in pairwise(bounds):
            assert top == previous_bottom

    def _lined_page(self, height: int = 8000, period: int = 30, ink: int = 24):
        """A page of word-shaped rows: ``ink`` pixels of content, then a gap, repeating.

        Drawn as separated marks rather than filled bars, because a row through a solid area is
        flat too — and cutting through one is correct. It is a row through *words* that must be
        avoided, and only a row of words has spread across the width.
        """
        from PIL import Image, ImageDraw

        image = Image.new("RGB", (2500, height), "white")
        draw = ImageDraw.Draw(image)
        for top in range(0, height, period):
            for x in range(0, 2500, 120):
                draw.rectangle((x, top, x + 70, top + ink - 1), fill="black")
        return image

    def test_a_cut_never_lands_inside_a_line_of_text(self) -> None:
        image = self._lined_page()
        bounds = vision.band_bounds(image)
        assert len(bounds) > 1
        for _, bottom in bounds[:-1]:
            assert vision.is_blank_row(image, bottom), f"row {bottom} is inside a line"

    def test_the_cut_moves_off_the_target_when_the_target_is_inked(self) -> None:
        """The seek is doing work, not landing on a blank target by luck."""
        image = self._lined_page()
        assert not vision.is_blank_row(image, vision.BAND_HEIGHT)
        assert vision.band_bounds(image)[0][1] != vision.BAND_HEIGHT


class TestTheModelIsOptional:
    def test_no_ollama_costs_nothing_but_itself(self, monkeypatch) -> None:
        monkeypatch.setattr(vision, "endpoint", lambda: "http://127.0.0.1:1")
        vision.installed_model.cache_clear()
        try:
            assert vision.installed_model() is None
            assert vision.recognize_image(b"not an image") == ""
        finally:
            vision.installed_model.cache_clear()

    def test_an_unknown_model_is_not_used(self, monkeypatch) -> None:
        """Only models this repo has a contract with are asked; a random tag is not a reader."""
        monkeypatch.setattr(vision, "_list_tags", lambda: {"llama3.2:latest", "deepseek-r1:14b"})
        vision.installed_model.cache_clear()
        try:
            assert vision.installed_model() is None
        finally:
            vision.installed_model.cache_clear()

    def test_a_preferred_model_is_found_by_its_bare_name(self, monkeypatch) -> None:
        monkeypatch.setattr(vision, "_list_tags", lambda: {"glm-ocr:latest", "llama3.2:latest"})
        vision.installed_model.cache_clear()
        try:
            assert vision.installed_model() == "glm-ocr"
        finally:
            vision.installed_model.cache_clear()

    def test_the_endpoint_honours_ollamas_own_convention(self, monkeypatch) -> None:
        monkeypatch.setenv("OLLAMA_HOST", "192.168.0.9:11434")
        assert vision.endpoint() == "http://192.168.0.9:11434"
        monkeypatch.setenv("OLLAMA_HOST", "")
        assert vision.endpoint() == "http://127.0.0.1:11434"
