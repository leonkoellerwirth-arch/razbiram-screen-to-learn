"""Deterministic identifiers for the capture pipeline.

The authoritative specification is ``docs/architecture/IDENTITY_ALGORITHMS.md``. This module is
the Python side of it; the browser extension carries a TypeScript twin. Both must produce
byte-identical output from identical inputs, so every step here is explicit: no locale-dependent
casing, no dict ordering, no platform hashing differences.

Raw option texts and question stems must not be logged or transmitted from here.
"""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

ALGORITHM_VERSIONS = {
    "questionFingerprint": "qfp:1",
    "stateFingerprint": "sfp:1",
    "captureId": "cid:1",
    "sourceId": "sid:1",
    "optionId": "oid:1",
    "cardId": "crd:1",
}

_TAG = re.compile(r"<[^>]*>")
_WHITESPACE = re.compile(r"\s+")
_LEADING_MARKER = re.compile(r"^[✓✔✗✘●○→]\s*")
_LEADING_KEYWORD = re.compile(r"^(?:correct|incorrect|right|wrong)[:.\s]\s*", re.IGNORECASE)
_TRAILING_PAREN = re.compile(r"\s*\((?:correct|incorrect|right answer|wrong)\)\s*$", re.IGNORECASE)


def strip_markup(text: str) -> str:
    """Remove tags, then decode entities.

    IDENTITY_ALGORITHMS.md is ambiguous here: it says to strip tags "before any other
    normalization" and, in the next sentence, to decode entities "first, then strip tags". The two
    orders are not equivalent — decoding first turns ``&lt;b&gt;`` into ``<b>``, which the tag
    pass would then delete, silently destroying text the user actually saw. Tags are stripped
    first so that only real markup is removed. For DOM-sourced text this is moot (the browser has
    already decoded entities); it matters only for raw HTML input.
    """
    return html.unescape(_TAG.sub("", text))


def collapse_whitespace(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def normalize_text(text: str) -> str:
    """Markup-stripped, NFC, whitespace-collapsed. Used for question stems and explanations."""
    return collapse_whitespace(unicodedata.normalize("NFC", strip_markup(text)))


def strip_feedback(text: str) -> str:
    """Remove correctness markers a reveal state may inject around option text.

    Applied in the documented order: leading Unicode marker, leading keyword, trailing
    parenthetical. Each rule applies once. A rule that would empty the string is skipped, because
    an empty option text is never the intended reading.
    """
    result = text.strip()
    for pattern in (_LEADING_MARKER, _LEADING_KEYWORD, _TRAILING_PAREN):
        candidate = pattern.sub("", result, count=1)
        if candidate.strip():
            result = candidate
    return result


def clean_text(text: str) -> str:
    """The ``cleanText`` of ``semantic-snapshot.v1``: option text with feedback markers removed.

    Idempotent, so callers may pass either raw or already-cleaned text.
    """
    return collapse_whitespace(unicodedata.normalize("NFC", strip_feedback(strip_markup(text))))


def _sha256_hex(blob: str) -> str:
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _join(*fields: str) -> str:
    return "\n".join(fields)


@dataclass(frozen=True)
class OptionState:
    """One option as observed in a single DOM state."""

    clean_text: str
    checked: bool
    visible_text: str


def question_fingerprint(
    *,
    origin: str,
    path: str,
    card_family: str,
    question_text: str,
    option_texts: Iterable[str],
) -> str:
    """The join key. Identical across question and reveal states of the same question.

    Option texts are sorted by Unicode code point, which is what makes the key survive a reveal
    state that randomizes option order (Golden case G13).
    """
    cleaned = sorted(clean_text(option) for option in option_texts)
    blob = _join(
        ALGORITHM_VERSIONS["questionFingerprint"],
        "origin:" + unicodedata.normalize("NFC", origin),
        "path:" + unicodedata.normalize("NFC", path),
        "family:" + card_family.lower(),
        "question:" + normalize_text(question_text),
        "option_count:" + str(len(cleaned)),
        "options:" + "\n".join(cleaned),
    )
    return _sha256_hex(blob)


def state_fingerprint(
    *,
    question_fp: str,
    option_states: Iterable[OptionState],
    explanation_texts: Iterable[str] = (),
) -> str:
    """Dedup key for one DOM state. Distinct question vs reveal, identical across rerenders."""
    ordered = sorted(option_states, key=lambda state: state.clean_text)
    per_option = "|".join(
        f"{state.clean_text}:{int(state.checked)}:{state.visible_text}" for state in ordered
    )
    explanation = "\n".join(normalize_text(text) for text in explanation_texts)
    blob = _join(
        ALGORITHM_VERSIONS["stateFingerprint"],
        "qfp:" + question_fp,
        "options:" + per_option,
        "explanation:" + explanation,
    )
    return _sha256_hex(blob)


def capture_id(
    *,
    created_at: str,
    origin: str,
    path: str,
    capture_state: str,
    question_fp: str,
    artifact_hashes: Sequence[str],
) -> str:
    blob = _join(
        ALGORITHM_VERSIONS["captureId"],
        "created:" + created_at,
        "origin:" + unicodedata.normalize("NFC", origin),
        "path:" + unicodedata.normalize("NFC", path),
        "state:" + capture_state,
        "qfp:" + question_fp,
        "artifacts:" + "\n".join(sorted(artifact_hashes)),
    )
    return "cap_" + _sha256_hex(blob)


def source_id(*, origin: str, path: str, question_fp: str) -> str:
    blob = _join(
        ALGORITHM_VERSIONS["sourceId"],
        "origin:" + unicodedata.normalize("NFC", origin),
        "path:" + unicodedata.normalize("NFC", path),
        "qfp:" + question_fp,
    )
    return "src_" + _sha256_hex(blob)[:32]


def option_id(*, source: str, option_text: str) -> str:
    blob = _join(
        ALGORITHM_VERSIONS["optionId"],
        "source_id:" + source,
        "clean_text:" + clean_text(option_text),
    )
    return "opt_" + _sha256_hex(blob)[:32]


def card_id(*, source: str) -> str:
    blob = _join(ALGORITHM_VERSIONS["cardId"], "source_id:" + source)
    return "q-" + _sha256_hex(blob)[:16]
