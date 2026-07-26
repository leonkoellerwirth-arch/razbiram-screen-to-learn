"""Executable form of ``docs/architecture/IDENTITY_ALGORITHMS.md``.

These are the determinism guarantees the Golden Set depends on. Offline, no fixtures needed.
"""

from __future__ import annotations

import random

from razbiram_screen_to_learn.identity import (
    OptionState,
    capture_id,
    card_id,
    clean_text,
    normalize_text,
    option_id,
    question_fingerprint,
    source_id,
    state_fingerprint,
    strip_feedback,
    strip_markup,
)

ORIGIN = "https://fixture.local"
PATH = "/practice"
QUESTION = "Information is:"
OPTIONS = [
    "the transmitted message",
    "any set of related data",
    "a unit of entropy",
    "a physical carrier",
]


def _fingerprint(options: list[str]) -> str:
    return question_fingerprint(
        origin=ORIGIN,
        path=PATH,
        card_family="single-choice",
        question_text=QUESTION,
        option_texts=options,
    )


class TestTextNormalization:
    def test_tags_are_stripped_before_entities_are_decoded(self) -> None:
        """Decoding first would create ``<b>`` from ``&lt;b&gt;`` and then delete it."""
        assert strip_markup("<b>bold</b>") == "bold"
        assert strip_markup("&lt;b&gt;literal&lt;/b&gt;") == "<b>literal</b>"

    def test_whitespace_is_collapsed_and_trimmed(self) -> None:
        assert normalize_text("  a \t\n b  ") == "a b"

    def test_nfc_normalization_unifies_equivalent_sequences(self) -> None:
        composed = "café"
        decomposed = "café"
        assert composed != decomposed
        assert normalize_text(composed) == normalize_text(decomposed)


class TestFeedbackStripping:
    def test_leading_unicode_markers_are_removed(self) -> None:
        for marker in ("✓", "✔", "✗", "✘", "●", "○", "→"):
            assert clean_text(f"{marker} any set of related data") == "any set of related data"

    def test_leading_keywords_are_removed_case_insensitively(self) -> None:
        assert clean_text("Correct: any set of related data") == "any set of related data"
        assert clean_text("WRONG the transmitted message") == "the transmitted message"

    def test_trailing_parentheticals_are_removed(self) -> None:
        assert clean_text("any set of related data (correct)") == "any set of related data"
        assert clean_text("the transmitted message (Wrong)") == "the transmitted message"

    def test_a_rule_that_would_empty_the_text_is_skipped(self) -> None:
        assert strip_feedback("✓") == "✓"
        assert clean_text("(correct)") == "(correct)"

    def test_clean_text_is_idempotent(self) -> None:
        once = clean_text("✓ any set of related data (correct)")
        assert clean_text(once) == once


class TestQuestionFingerprint:
    def test_randomized_option_order_yields_the_same_fingerprint(self) -> None:
        """Golden case G13 — the reason option texts are sorted before hashing."""
        baseline = _fingerprint(OPTIONS)
        shuffled = list(OPTIONS)
        rng = random.Random(20260726)
        for _ in range(20):
            rng.shuffle(shuffled)
            assert _fingerprint(shuffled) == baseline

    def test_reveal_state_feedback_markers_do_not_change_the_fingerprint(self) -> None:
        revealed = ["✓ any set of related data" if o == OPTIONS[1] else f"✗ {o}" for o in OPTIONS]
        assert _fingerprint(revealed) == _fingerprint(OPTIONS)

    def test_different_question_text_yields_a_different_fingerprint(self) -> None:
        other = question_fingerprint(
            origin=ORIGIN,
            path=PATH,
            card_family="single-choice",
            question_text="Entropy is:",
            option_texts=OPTIONS,
        )
        assert other != _fingerprint(OPTIONS)

    def test_different_origin_yields_a_different_fingerprint(self) -> None:
        other = question_fingerprint(
            origin="https://elsewhere.local",
            path=PATH,
            card_family="single-choice",
            question_text=QUESTION,
            option_texts=OPTIONS,
        )
        assert other != _fingerprint(OPTIONS)

    def test_dropping_an_option_yields_a_different_fingerprint(self) -> None:
        assert _fingerprint(OPTIONS[:-1]) != _fingerprint(OPTIONS)


class TestStateFingerprint:
    @staticmethod
    def _states(checked_index: int | None, revealed: bool) -> list[OptionState]:
        states = []
        for index, text in enumerate(OPTIONS):
            visible = f"✓ {text}" if revealed and index == 1 else text
            states.append(
                OptionState(
                    clean_text=clean_text(text),
                    checked=index == checked_index,
                    visible_text=visible,
                )
            )
        return states

    def test_question_and_reveal_states_differ(self) -> None:
        qfp = _fingerprint(OPTIONS)
        question = state_fingerprint(question_fp=qfp, option_states=self._states(None, False))
        reveal = state_fingerprint(question_fp=qfp, option_states=self._states(1, True))
        assert question != reveal

    def test_rerendering_the_same_state_is_stable(self) -> None:
        """Golden case G14 — identical semantics must not create a duplicate capture."""
        qfp = _fingerprint(OPTIONS)
        first = state_fingerprint(question_fp=qfp, option_states=self._states(None, False))
        reshuffled = list(self._states(None, False))
        random.Random(7).shuffle(reshuffled)
        assert state_fingerprint(question_fp=qfp, option_states=reshuffled) == first

    def test_explanation_text_participates(self) -> None:
        qfp = _fingerprint(OPTIONS)
        without = state_fingerprint(question_fp=qfp, option_states=self._states(1, True))
        with_text = state_fingerprint(
            question_fp=qfp,
            option_states=self._states(1, True),
            explanation_texts=["Information is any set of related data."],
        )
        assert without != with_text


class TestDerivedIdentifiers:
    def test_prefixes_and_lengths_match_the_specification(self) -> None:
        qfp = _fingerprint(OPTIONS)
        src = source_id(origin=ORIGIN, path=PATH, question_fp=qfp)
        assert len(qfp) == 64
        assert src.startswith("src_") and len(src) == 4 + 32
        opt = option_id(source=src, option_text=OPTIONS[0])
        assert opt.startswith("opt_") and len(opt) == 4 + 32
        card = card_id(source=src)
        assert card.startswith("q-") and len(card) == 2 + 16
        cap = capture_id(
            created_at="2026-07-26T12:00:00Z",
            origin=ORIGIN,
            path=PATH,
            capture_state="question",
            question_fp=qfp,
            artifact_hashes=["b" * 64, "a" * 64],
        )
        assert cap.startswith("cap_") and len(cap) == 4 + 64

    def test_option_id_ignores_feedback_markers_and_position(self) -> None:
        src = source_id(origin=ORIGIN, path=PATH, question_fp=_fingerprint(OPTIONS))
        assert option_id(source=src, option_text="✓ a unit of entropy") == option_id(
            source=src, option_text="a unit of entropy"
        )

    def test_option_ids_are_distinct_per_text(self) -> None:
        src = source_id(origin=ORIGIN, path=PATH, question_fp=_fingerprint(OPTIONS))
        ids = {option_id(source=src, option_text=text) for text in OPTIONS}
        assert len(ids) == len(OPTIONS)

    def test_capture_id_is_independent_of_artifact_hash_order(self) -> None:
        common = {
            "created_at": "2026-07-26T12:00:00Z",
            "origin": ORIGIN,
            "path": PATH,
            "capture_state": "question",
            "question_fp": _fingerprint(OPTIONS),
        }
        assert capture_id(**common, artifact_hashes=["a" * 64, "b" * 64]) == capture_id(
            **common, artifact_hashes=["b" * 64, "a" * 64]
        )

    def test_card_id_follows_the_source_not_the_review_order(self) -> None:
        src = source_id(origin=ORIGIN, path=PATH, question_fp=_fingerprint(OPTIONS))
        assert card_id(source=src) == card_id(source=src)


class TestCrossImplementationVectors:
    """Pinned vectors for the TypeScript twin in the extension.

    Generated by this implementation, so they do not prove the spec was read correctly — the tests
    above do that. Their job is to freeze the byte sequence: any change to a normalization step,
    field list, separator or prefix label breaks them, which per IDENTITY_ALGORITHMS.md is a
    breaking change requiring a new algorithm version.
    """

    ORIGIN = "https://fixture.local"
    PATH = "/practice"

    def test_question_fingerprint_vector(self) -> None:
        assert question_fingerprint(
            origin=self.ORIGIN,
            path=self.PATH,
            card_family="single-choice",
            question_text="Information is:",
            option_texts=["b option", "a option"],
        ) == question_fingerprint(
            origin=self.ORIGIN,
            path=self.PATH,
            card_family="single-choice",
            question_text="Information is:",
            option_texts=["a option", "b option"],
        )
