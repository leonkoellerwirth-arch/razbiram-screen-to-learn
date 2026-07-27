"""Whether a piece of recognised text can be trusted enough to publish as an answer.

Every reader in this repo tries to read a row correctly. This module asks the question none of
them can answer about themselves: *did it work?* That question is what turns the failure mode
observed on a real practice assessment — four of fourteen exported cards carrying a mangled
correct answer, silently, at tier ``source-verified`` — into a card that says so.

The point is generality. A better reader fixes one layout; a verdict on the text fixes every
layout, including the ones nobody has seen yet, because it does not care how the text was
obtained. What it measures is only ever *evidence of damage* — never whether the words are true:

* **a word written in two alphabets** — OCR swapping Latin letters for Cyrillic lookalikes is
  invisible to a reader and fatal to a learner;
* **furniture left in the text** — the widget glyphs and table rules that survive as characters;
* **too few letters to be prose** — a row that came back as mostly punctuation.

A verdict never repairs anything and never blocks anything by itself. It attaches to the card, and
the export path decides: unreadable text cannot be `source-verified`, so it lands in the draft as
`needs-review` with the reason stated, where a person fixes it. That is the whole guarantee —
**nothing we could not read leaves as if we had read it.**
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

#: Characters that are page furniture rather than language: widget glyphs, table rules, the numero
#: sign a toggle switch OCRs into. A single one is enough to call the row damaged, because none of
#: them occurs in a sentence a quiz would print.
FURNITURE = frozenset("|@¤§¶©®™\\^~`")

#: Below this share of letters (over non-space characters) a row is not prose.
MIN_LETTER_RATIO = 0.55

#: Rows shorter than this are not judged on ratios — "True", "False", "Yes" are legitimate answers
#: and would fail every statistical test written for a sentence.
SHORT_TEXT_CHARS = 12

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


@dataclass(frozen=True)
class Verdict:
    """What is wrong with a piece of text, if anything. Empty ``reasons`` means it reads."""

    ok: bool
    reasons: tuple[str, ...] = field(default=())

    def __bool__(self) -> bool:
        return self.ok


def _script_of(char: str) -> str:
    """LATIN, CYRILLIC, GREEK… — the alphabet a letter belongs to, from its Unicode name."""
    try:
        name = unicodedata.name(char)
    except ValueError:
        return ""
    return name.split(" ")[0]


def mixed_script_words(text: str) -> list[str]:
    """Words written in more than one alphabet at once — a recogniser slip, never a language."""
    suspect = []
    for word in _WORD_RE.findall(text):
        scripts = {_script_of(char) for char in word if char.isalpha()}
        scripts.discard("")
        if len(scripts) > 1:
            suspect.append(word)
    return suspect


#: A minority script covering no more than this share of a line's words is read as substitution
#: rather than as language. Set from the observed case: "To manage complexity, maximize value,
#: optimize predictability and control risk" came back with its first two words in Cyrillic — two
#: words out of nine.
MINORITY_SCRIPT_SHARE = 0.25

#: Below this many words a script count says nothing: a two-word answer in the "wrong" script is
#: as likely to be a quoted term as a misreading.
MIN_WORDS_FOR_SCRIPT_TEST = 4


def stray_script_words(text: str) -> list[str]:
    """Words in a different alphabet from the rest of the line, few enough to be a misreading.

    The corruption that started this module does not mix alphabets inside a word — it replaces
    whole words with lookalike ones: `To manage` came back as two entirely Cyrillic words inside
    an otherwise English sentence. Nothing about either word is malformed; only the company it
    keeps gives it away.

    A document may of course mix scripts: Bulgarian material quoting "Sprint Backlog" is ordinary
    and this tool reads it on purpose. What is not ordinary is a *handful* of words in the other
    alphabet. The tradeoff is deliberate and one-sided — a Bulgarian sentence carrying a single
    English loanword will be flagged and sent to review, which costs a click, while the reverse
    error ships a learner an answer nobody can read.
    """
    words = _WORD_RE.findall(text)
    if len(words) < MIN_WORDS_FOR_SCRIPT_TEST:
        return []

    by_script: dict[str, list[str]] = {}
    for word in words:
        scripts = [_script_of(c) for c in word if c.isalpha()]
        if not scripts:
            continue
        dominant = max(set(scripts), key=scripts.count)
        by_script.setdefault(dominant, []).append(word)

    if len(by_script) < 2:
        return []
    ranked = sorted(by_script.items(), key=lambda kv: -len(kv[1]))
    stray = [word for _, group in ranked[1:] for word in group]
    return stray if len(stray) / len(words) <= MINORITY_SCRIPT_SHARE else []


def _letter_ratio(text: str) -> float:
    dense = [c for c in text if not c.isspace()]
    if not dense:
        return 0.0
    return sum(1 for c in dense if c.isalpha()) / len(dense)


def readability(text: str) -> Verdict:
    """Judge one piece of recognised text.

    Deliberately conservative: it reports damage it can point at, and stays silent otherwise. A
    verdict that fired on merely unusual text would push real answers into review and train people
    to click past the warning, which costs more than the corruption it was meant to catch.
    """
    stripped = text.strip()
    reasons: list[str] = []

    if not stripped:
        return Verdict(False, ("the text is empty",))

    mixed = mixed_script_words(stripped)
    if mixed:
        reasons.append(f"written in two alphabets at once: {', '.join(mixed[:3])}")

    stray = stray_script_words(stripped)
    if stray:
        reasons.append(f"a few words in another alphabet than the rest: {', '.join(stray[:3])}")

    furniture = sorted({c for c in stripped if c in FURNITURE})
    if furniture:
        reasons.append(f"page furniture left in the text: {' '.join(furniture)}")

    if len(stripped) >= SHORT_TEXT_CHARS and _letter_ratio(stripped) < MIN_LETTER_RATIO:
        reasons.append("too few letters to be prose")

    return Verdict(not reasons, tuple(reasons))


def _dominant_script(text: str) -> str:
    """The alphabet most of a line's letters are written in."""
    scripts = [_script_of(c) for c in text if c.isalpha()]
    scripts = [s for s in scripts if s]
    return max(set(scripts), key=scripts.count) if scripts else ""


def fold_homoglyphs(text: str) -> str:
    """Rewrite a mixed-alphabet word into the alphabet most of its letters already use.

    Only touches words `mixed_script_words` names, and only the characters that have an unambiguous
    counterpart. A word that is genuinely half Cyrillic stays as it is and stays reported: this
    repairs the recogniser's slip, it does not translate anyone's material.
    """
    if not mixed_script_words(text) and not stray_script_words(text):
        return text

    out = []
    for word in re.split(r"(\W+)", text, flags=re.UNICODE):
        if not word or not word[0].isalpha():
            out.append(word)
            continue
        scripts = [_script_of(c) for c in word if c.isalpha()]
        if not scripts:
            out.append(word)
            continue
        majority = _dominant_script(text)
        if not majority or set(scripts) == {majority}:
            out.append(word)
            continue
        table = _CYRILLIC_TO_LATIN if majority == "LATIN" else _LATIN_TO_CYRILLIC
        out.append("".join(table.get(c, c) for c in word))
    return "".join(out)


#: Letters that are drawn identically in the two alphabets, which is why a recogniser swaps them.
_CYRILLIC_TO_LATIN = {
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P",
    "С": "C", "Т": "T", "У": "Y", "Х": "X", "а": "a", "е": "e", "о": "o", "р": "p",
    "с": "c", "у": "y", "х": "x", "к": "k", "м": "m", "т": "t", "в": "b", "н": "h",
}  # fmt: skip
_LATIN_TO_CYRILLIC = {latin: cyr for cyr, latin in _CYRILLIC_TO_LATIN.items()}
