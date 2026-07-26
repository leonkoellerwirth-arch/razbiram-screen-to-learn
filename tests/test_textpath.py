"""The text intake path: segmentation, answer binding, family detection and OCR.

This path exists because an image and a PDF carry no DOM. Every test here pins behaviour that a
photographed or scanned page depends on, and the two homoglyph tests pin the rule that keeps
Bulgarian material correct.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from razbiram_screen_to_learn.export import export_deck
from razbiram_screen_to_learn.ocr import IMAGE_SUFFIXES, recognize_image
from razbiram_screen_to_learn.pipeline import LIVE_CAPABILITIES, process_text
from razbiram_screen_to_learn.textcards import fold_letters
from razbiram_screen_to_learn.textseg import extract_answer_key, parse_lines

THREE_FAMILIES = """1. Which organ produces insulin?
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


def families(text: str) -> list[str]:
    return [card.family for card in process_text(text, title="t").document.cards]


def test_all_three_families_are_detected_and_bound() -> None:
    result = process_text(THREE_FAMILIES, title="t")
    assert [c.family for c in result.document.cards] == [
        "single-choice",
        "multiple-select",
        "true-false",
    ]
    assert {c.answerEvidenceTier for c in result.document.cards} == {"source-verified"}
    assert result.export.deck is not None
    assert len(result.export.deck["cards"]) == 3
    assert result.export.blocked_card_ids == []


def test_multiple_select_binds_every_declared_letter() -> None:
    card = process_text(THREE_FAMILIES, title="t").document.cards[1]
    correct = [o.text for o in (card.options or []) if o.isCorrect]
    assert correct == ["Iron", "Copper"]


def test_answer_key_on_one_line_is_read() -> None:
    single_line = THREE_FAMILIES.replace(
        "Answers:\n1. B\n2. A, C\n3. A\n", "Answers: 1-B, 2-A C, 3-A\n"
    )
    result = process_text(single_line, title="t")
    assert {c.answerEvidenceTier for c in result.document.cards} == {"source-verified"}


def test_in_question_answer_line_is_not_mistaken_for_a_key_section() -> None:
    """ "Answer: B" inside a block must not truncate segmentation at that line."""
    text = "1. Q one?\nA) x\nB) y\nC) z\nAnswer: B\n\n2. Q two?\nA) p\nB) q\nC) r\nAnswer: A\n"
    lines = parse_lines(text)
    key, start = extract_answer_key(lines)
    assert key == {} and start is None
    result = process_text(text, title="t")
    assert len(result.document.cards) == 2
    assert {c.answerEvidenceTier for c in result.document.cards} == {"source-verified"}


def test_without_an_answer_key_nothing_is_invented() -> None:
    text = "1. Which organ produces insulin?\nA) Liver\nB) Pancreas\nC) Kidney\n"
    card = process_text(text, title="t").document.cards[0]
    assert card.answerEvidenceTier == "source-ambiguous"
    assert card.correctOptionIds == []
    assert "no-answer-key" in card.review.blockingReasons
    # An unevidenced card must not reach the export.
    assert process_text(text, title="t").export.deck is None


def test_two_options_are_not_true_false_unless_they_read_as_the_pair() -> None:
    text = "1. Pick one.\nA) Yes\nB) Maybe\n\nAnswers:\n1. A\n"
    assert families(text) == ["single-choice"]


def test_latin_key_binds_when_ocr_returned_cyrillic_lookalikes() -> None:
    """OCR reads the key in Cyrillic while the options are Latin A)/C).

    Same glyphs, different code points — without folding, nothing binds.
    """
    text = (
        "1. Select all that apply. Which of these are metals?\n"
        "A) Iron\nB) Oxygen\nC) Copper\nD) Helium\n\n"
        "Answers:\n1. А, С\n"  # Cyrillic А, С
    )
    card = process_text(text, title="t").document.cards[0]
    assert [o.text for o in (card.options or []) if o.isCorrect] == ["Iron", "Copper"]


def test_cyrillic_markers_are_never_folded_to_latin() -> None:
    """Bulgarian runs А, Б, В, Г — "В" is the THIRD option, not Latin "B", the second."""
    text = "1. Въпрос?\nА) one\nБ) two\nВ) three\nГ) four\n\nОтговори:\n1. В\n"
    card = process_text(text, title="t").document.cards[0]
    assert [o.text for o in (card.options or []) if o.isCorrect] == ["three"]


def test_fold_letters_picks_the_alphabet_from_the_markers() -> None:
    # A Cyrillic-only marker proves the document numbers in Cyrillic.
    assert fold_letters(["B"], ["А", "Б", "В"]) == ["В"]
    # No Cyrillic-only marker: fold towards Latin.
    assert fold_letters(["С"], ["A", "B", "C"]) == ["C"]


def test_segmentation_reports_a_block_it_cannot_resolve() -> None:
    result = process_text("Just a heading with no options at all\n", title="t")
    assert result.document.cards == []
    assert result.unsupported == ["block-1"]


def test_an_in_question_answer_line_never_truncates_the_document() -> None:
    """A block whose stem OCR'd down to a single letter must not swallow the rest of the page.

    "Answer: B" matches the answer-key heading vocabulary, and a following line like "2. B" reads
    like a key row. Treating the pair as a key section silently discarded every later question.
    """
    text = (
        "1. Q one?\nA) x\nB) y\nC) z\nAnswer: B\n\n"
        "2. B\nA) p\nB) q\nC) r\n\n"
        "3. Q three?\nA) m\nB) n\nC) o\nAnswer: C\n"
    )
    key, start = extract_answer_key(parse_lines(text))
    assert key == {} and start is None
    assert len(process_text(text, title="t").document.cards) == 3


def test_a_scattered_key_lookalike_does_not_join_the_key_section() -> None:
    """Key rows are a contiguous run; a matching line further down is not part of it."""
    text = "1. Q?\nA) x\nB) y\nC) z\n\nAnswers:\n1. B\n\nUnrelated prose here.\n2. C\n"
    key, _ = extract_answer_key(parse_lines(text))
    assert key == {1: ["B"]}


def test_deck_key_stays_schema_shaped_for_a_long_title() -> None:
    """Truncation used to land on a hyphen and emit "…eight--5d8c5119"."""
    result = process_text(THREE_FAMILIES, title="one two three four five six seven eight nine")
    deck_key = result.document.deck.deckKey
    assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", deck_key), deck_key


def test_locale_reaches_the_cards_not_only_the_deck() -> None:
    """Every localized field must use the caller's locale; a stray "und" renders as nothing."""
    result = process_text(THREE_FAMILIES, title="t", locale="en")
    assert set(result.document.deck.title) == {"en"}
    for card in result.document.cards:
        assert set(card.prompt.value) == {"en"}
        if card.statement is not None:
            assert set(card.statement.value) == {"en"}


def test_export_refuses_an_unevidenced_card_on_its_own() -> None:
    """The tier gate must live in the exporter, not only in the validator.

    A caller that reads ``export.deck`` without inspecting issues must still never receive a card
    whose answer was never evidenced.
    """
    result = process_text(THREE_FAMILIES, title="t")
    tampered = result.document.model_copy(
        update={
            "cards": [
                card.model_copy(update={"answerEvidenceTier": "source-ambiguous"})
                for card in result.document.cards
            ]
        }
    )
    out = export_deck(tampered, capabilities=set(LIVE_CAPABILITIES))
    assert out.deck is None
    assert len(out.blocked) == len(result.document.cards)
    assert all("not exportable" in blocked.reason for blocked in out.blocked)


def test_a_block_without_a_question_is_reported_as_such() -> None:
    """The reported reason must name the block's actual defect, not a missing answer key."""
    result = process_text("A) x\nB) y\nC) z\n", title="t")
    assert result.document.cards == []
    assert result.unsupported == ["block-1"]


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed")
def test_ocr_reads_a_rendered_quiz_end_to_end() -> None:
    image = Path(__file__).resolve().parents[1] / "fixtures" / "images" / "quiz.png"
    if not image.is_file():
        pytest.skip("no image fixture committed")
    assert image.suffix in IMAGE_SUFFIXES
    recognised = recognize_image(image.read_bytes(), image.suffix)
    result = process_text(recognised.text, title="quiz", source_kind="image-upload")
    assert [c.family for c in result.document.cards] == [
        "single-choice",
        "multiple-select",
        "true-false",
    ]
    assert result.export.deck is not None
    assert len(result.export.deck["cards"]) == 3
