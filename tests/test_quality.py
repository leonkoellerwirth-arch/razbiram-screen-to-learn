"""The verdict that decides whether recognised text may be published as an answer.

Written from four real failures, not from imagination. A practice assessment exported fourteen
cards; four carried a correct answer nobody could read, and all four passed every check the
pipeline had, because something *was* marked correct and the text *was* non-empty. These tests pin
the difference between "we read a row" and "the row is legible".
"""

from __future__ import annotations

from razbiram_screen_to_learn.pipeline import process_text
from razbiram_screen_to_learn.quality import fold_homoglyphs, mixed_script_words, readability

#: The observed corruption: Latin letters swapped for Cyrillic lookalikes inside English words.
HOMOGLYPH_ANSWER = "То тападе complexity, maximize value, optimize predictability and control risk"


class TestReadability:
    def test_plain_prose_reads(self) -> None:
        assert readability("There is no such thing as Sprint 0 in Scrum").ok

    def test_a_short_answer_is_not_penalised(self) -> None:
        """ "True", "False", "Yes" are answers, not damage."""
        for answer in ("True", "False", "Yes", "None of the above"):
            assert readability(answer).ok, answer

    def test_a_word_in_two_alphabets_is_damage(self) -> None:
        verdict = readability("To taпaдe complexity, maximize value and control risk")
        assert not verdict.ok
        assert any("two alphabets" in reason for reason in verdict.reasons)

    def test_a_few_whole_words_in_another_alphabet_are_damage(self) -> None:
        """The observed shape: entire words substituted, each one well-formed on its own."""
        verdict = readability(HOMOGLYPH_ANSWER)
        assert not verdict.ok
        assert any("another alphabet" in reason for reason in verdict.reasons)

    def test_a_document_may_mix_scripts_freely(self) -> None:
        """Bulgarian material quoting an English term is ordinary. Only a mixed *word* is not."""
        assert readability("Какво е Sprint Backlog според Scrum Guide?").ok

    def test_page_furniture_is_damage(self) -> None:
        assert not readability("@ | Scrum does not recognise Project Managers; |").ok

    def test_empty_text_is_damage(self) -> None:
        assert not readability("   ").ok


class TestFoldHomoglyphs:
    def test_lookalike_letters_are_repaired_towards_the_line_s_script(self) -> None:
        assert fold_homoglyphs(HOMOGLYPH_ANSWER).startswith("To ")

    def test_what_cannot_be_repaired_stays_reported(self) -> None:
        """The fold maps only letters drawn identically in both alphabets.

        Cyrillic п and д stand in for n and g on this material, but they are not the same glyph, so
        folding them would be a guess. The word stays half-repaired and therefore still fails
        `readability` — which sends the card to review instead of publishing a plausible-looking
        answer. Half a repair is allowed; half a guess is not.
        """
        repaired = fold_homoglyphs(HOMOGLYPH_ANSWER)
        assert mixed_script_words(repaired)
        assert not readability(repaired).ok

    def test_wholly_cyrillic_text_is_left_alone(self) -> None:
        bulgarian = "Кой отговаря за Product Backlog"
        assert fold_homoglyphs(bulgarian) == bulgarian


def test_an_unreadable_answer_cannot_be_source_verified() -> None:
    """The guarantee, end to end: a marked answer we could not read never exports as evidence.

    Before this check the card below exported at tier `source-verified` — an answer key was
    present, so correctness was "read" — carrying an option nobody could make sense of.
    """
    result = process_text(
        "1. What is the purpose of Sprint 0?\n"
        "A) @ | Therei h thi Sprint 0 in 5 |\n"
        "B) A real, readable distractor about planning\n"
        "C) Another readable distractor about analysis\n"
        "\nAnswers:\n1. A\n",
        title="damaged",
    )
    card = result.document.cards[0]
    assert card.answerEvidenceTier == "source-ambiguous"
    assert "unreadable-answer-text" in card.review.blockingReasons
    assert result.export.deck is None
