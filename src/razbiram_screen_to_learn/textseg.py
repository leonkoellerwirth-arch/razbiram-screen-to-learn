"""Deterministic segmentation of raw text into question blocks.

The DOM extractor in ``extract.py`` reads structured markup. OCR and PDF intake produce no DOM at
all — only lines of text — so this module supplies the missing layer. It is a faithful port of
razbiram.com's ``app/src/lib/ingest/segment.ts``; keeping the two in step is what ADR 009 is about.

Pure string work. A block the segmenter cannot resolve is reported upstream, never silently
dropped and never "fixed". Nothing here decides correctness — that is ``textcards.py``.

Markers are matched in Latin AND Cyrillic because the primary corpus is Bulgarian exam material.
That is marker vocabulary, not a language branch: the content language is never inspected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

LineKind = Literal["option", "numbered", "text", "blank"]

# A single letter marker: Latin A-Z or Cyrillic А-Я, followed by ) . : ] or a space-dash.
OPTION_RE = re.compile(r"^\(?([A-Za-zА-Яа-я])[)\].:]\s+(.+)$")
BULLET_RE = re.compile(r"^[-–—•*·]\s+(.+)$")
NUMBERED_RE = re.compile(
    r"^(?:(?:frage|question|q|въпрос|aufgabe)\s*)?(\d{1,3})\s*[)\].:]\s*(.*)$",
    re.IGNORECASE,
)
ANSWER_INLINE_RE = re.compile(
    r"(?:answer|antwort|l[oö]sung|correct|solution|отговор|верен\s+отговор)"
    r"\s*[:\-–]?\s*([A-Za-zА-Яа-я](?:\s*[,;/&+]\s*[A-Za-zА-Яа-я])*)\s*$",
    re.IGNORECASE,
)
#: The heading of a trailing answer-key section. Anything after it is captured, because real
#: material writes the key both ways: on its own line with rows beneath, or all on one line
#: ("Answers: 1-B, 2-A C, 3-A"). Which of the two it is, is decided by what actually parses.
ANSWER_KEY_HEADING_RE = re.compile(
    r"^(?:answers?|l[oö]sungen|antworten|solutions?|answer\s+key|отговори|ключ)\b\s*:?\s*(.*)$",
    re.IGNORECASE,
)
#: "1-B", "2. A, C" — one question's entry inside a single-line key.
ANSWER_KEY_INLINE_PAIR_RE = re.compile(
    r"(\d{1,3})\s*[-–)\].:]\s*([A-Za-zА-Яа-я](?:\s*[,;/&+]?\s*[A-Za-zА-Яа-я])*)"
)
#: A key row whose number OCR left stranded on its own line, e.g. "1." above a line reading "B".
ANSWER_KEY_NUMBER_ONLY_RE = re.compile(r"^(\d{1,3})\s*[)\].:\-–]?\s*$")
ANSWER_KEY_ROW_RE = re.compile(
    r"^(\d{1,3})\s*[)\].:\-–]\s*([A-Za-zА-Яа-я](?:\s*[,;/&+]\s*[A-Za-zА-Яа-я])*)\s*$"
)
#: Inline correctness marks. Deliberately conservative — a stray asterisk is common in OCR.
CORRECT_MARK_RE = re.compile(
    r"(?:^|\s)(?:[✓✔✅☑]|\(\s*(?:correct|richtig|верен|верно)\s*\))(?:\s|$)",
    re.IGNORECASE,
)

_WHITESPACE_RUN_RE = re.compile(r"\s{2,}")


@dataclass(frozen=True)
class ParsedLine:
    """One source line, classified. ``text`` has any leading marker removed."""

    n: int
    raw: str
    text: str
    kind: LineKind
    marked: bool
    marker: str | None = None


@dataclass
class RawBlock:
    """One question and its options, as found in the text."""

    index: int
    question_lines: list[ParsedLine] = field(default_factory=list)
    option_lines: list[ParsedLine] = field(default_factory=list)
    line_start: int = 0
    line_end: int = 0
    #: Letters named by an inline "Answer: B" line inside this block.
    inline_answers: list[str] = field(default_factory=list)


#: question index (1-based, as printed) -> the letters its answer key declares correct.
AnswerKey = dict[int, list[str]]


def strip_correct_mark(value: str) -> str:
    return _WHITESPACE_RUN_RE.sub(" ", CORRECT_MARK_RE.sub(" ", value)).strip()


def split_answer_letters(cell: str) -> list[str]:
    """Split an answer cell like "B, D" or "A/C" into normalized upper-case letters."""
    parts = (piece.strip().upper() for piece in re.split(r"[,;/&+\s]+", cell))
    return [part for part in parts if len(part) == 1]


def parse_lines(text: str) -> list[ParsedLine]:
    lines: list[ParsedLine] = []
    for n, raw in enumerate(re.split(r"\r?\n", text)):
        trimmed = raw.strip()
        if trimmed == "":
            lines.append(ParsedLine(n=n, raw=raw, text="", kind="blank", marked=False))
            continue

        marked = CORRECT_MARK_RE.search(trimmed) is not None
        clean = strip_correct_mark(trimmed)

        option = OPTION_RE.match(clean)
        if option:
            lines.append(
                ParsedLine(
                    n=n,
                    raw=raw,
                    text=option.group(2).strip(),
                    kind="option",
                    marker=option.group(1).upper(),
                    marked=marked,
                )
            )
            continue

        bullet = BULLET_RE.match(clean)
        if bullet:
            lines.append(
                ParsedLine(n=n, raw=raw, text=bullet.group(1).strip(), kind="option", marked=marked)
            )
            continue

        numbered = NUMBERED_RE.match(clean)
        if numbered:
            lines.append(
                ParsedLine(
                    n=n,
                    raw=raw,
                    text=numbered.group(2).strip(),
                    kind="numbered",
                    marker=numbered.group(1),
                    marked=marked,
                )
            )
            continue

        lines.append(ParsedLine(n=n, raw=raw, text=clean, kind="text", marked=marked))
    return lines


def extract_answer_key(lines: list[ParsedLine]) -> tuple[AnswerKey, int | None]:
    """Find a trailing "Answers:" section.

    Returns the parsed key and the line index where that section begins, so block segmentation can
    stop there instead of reading the key rows as questions.
    """
    for i, line in enumerate(lines):
        if line.kind == "blank":
            continue
        heading = ANSWER_KEY_HEADING_RE.match(line.raw.strip())
        if not heading:
            continue

        remainder = heading.group(1).strip()

        # Form 1 — the whole key on the heading line itself ("Answers: 1-B, 2-A C").
        answer_key: AnswerKey = {}
        for number, cell in ANSWER_KEY_INLINE_PAIR_RE.findall(remainder):
            letters = split_answer_letters(cell)
            if letters:
                answer_key[int(number)] = letters
        if answer_key:
            return answer_key, i

        # Form 2 — a standalone heading with rows beneath it.
        #
        # The remainder must be empty. "Answer: B" inside a question also matches the heading
        # vocabulary, and treating it as a section start would truncate every question after it —
        # silently, and catastrophically, since OCR readily produces a line whose stem is a single
        # letter that then reads like a key row.
        if remainder:
            continue

        # Rows must be contiguous: a key section is a run, not scattered lookalikes further down.
        # OCR readily breaks "1. B" across two lines, so a bare number is carried to the letters
        # that follow it rather than ending the run.
        pending: int | None = None
        for row_line in lines[i + 1 :]:
            if row_line.kind == "blank":
                continue
            stripped = row_line.raw.strip()

            row = ANSWER_KEY_ROW_RE.match(stripped)
            if row:
                letters = split_answer_letters(row.group(2))
                if letters:
                    answer_key[int(row.group(1))] = letters
                pending = None
                continue

            number = ANSWER_KEY_NUMBER_ONLY_RE.match(stripped)
            if number:
                pending = int(number.group(1))
                continue

            if pending is not None:
                letters = split_answer_letters(stripped)
                if letters:
                    answer_key[pending] = letters
                    pending = None
                    continue

            break
        if answer_key:
            return answer_key, i

    return {}, None


def segment_blocks(lines: list[ParsedLine], stop_at: int | None) -> list[RawBlock]:
    """Group lines into question blocks.

    A block opens on a numbered line, or on a text line that directly precedes an option run. It
    closes when the next block opens.
    """
    end = stop_at if stop_at is not None else len(lines)
    blocks: list[RawBlock] = []
    current: RawBlock | None = None
    fallback_index = 0

    def restarts_options(position: int) -> bool:
        """Whether the next thing after ``position`` is an option run starting over.

        The boundary between two questions, when the material does not spell it out. Numbering
        cannot be relied on — OCR drops a leading digit readily, and the moment it does, treating
        numbers as the anchor merges two questions into one. A marker sequence running A, B, C, D
        and then A again is unambiguous, and it survives a lost digit.
        """
        for ahead in lines[position + 1 : end]:
            if ahead.kind == "blank":
                continue
            if (
                ahead.kind != "option"
                or not ahead.marker
                or not current
                or not current.option_lines
            ):
                return False
            markers = [line.marker for line in current.option_lines if line.marker]
            return bool(markers) and ahead.marker <= markers[-1]
        return False

    def close() -> None:
        nonlocal current
        if current and (current.option_lines or current.question_lines):
            blocks.append(current)
        current = None

    for position, line in enumerate(lines[:end]):
        if line.kind == "blank":
            continue

        # An option run starting over means the previous question ended, whatever the numbering did.
        if line.kind == "option" and restarts_options(position - 1):
            close()

        inline = ANSWER_INLINE_RE.search(line.raw.strip())
        if inline and current:
            current.inline_answers = split_answer_letters(inline.group(1))
            current.line_end = line.n
            continue

        if line.kind == "numbered":
            close()
            fallback_index += 1
            marker_index = int(line.marker) if line.marker and line.marker.isdigit() else 0
            current = RawBlock(
                index=marker_index or fallback_index,
                question_lines=[line] if line.text else [],
                line_start=line.n,
                line_end=line.n,
            )
            continue

        if line.kind == "option":
            if current is None:
                fallback_index += 1
                current = RawBlock(index=fallback_index, line_start=line.n, line_end=line.n)
            current.option_lines.append(line)
            current.line_end = line.n
            continue

        # Plain text: a continuation of the question, or the start of a new one once options ran.
        if current is not None and current.option_lines:
            if not restarts_options(position):
                # A wrapped answer. Join it to the option it belongs to rather than cutting here.
                previous = current.option_lines[-1]
                current.option_lines[-1] = ParsedLine(
                    n=previous.n,
                    raw=previous.raw,
                    text=f"{previous.text} {line.text}".strip(),
                    kind="option",
                    marker=previous.marker,
                    marked=previous.marked or line.marked,
                )
                current.line_end = line.n
                continue
            close()
            fallback_index += 1
            current = RawBlock(
                index=fallback_index,
                question_lines=[line],
                line_start=line.n,
                line_end=line.n,
            )
            continue
        if current is None:
            fallback_index += 1
            current = RawBlock(
                index=fallback_index,
                question_lines=[line],
                line_start=line.n,
                line_end=line.n,
            )
            continue
        current.question_lines.append(line)
        current.line_end = line.n

    close()
    return blocks


def segment(text: str) -> tuple[list[RawBlock], AnswerKey]:
    lines = parse_lines(text)
    answer_key, key_section_start = extract_answer_key(lines)
    return segment_blocks(lines, key_section_start), answer_key


def block_question_text(block: RawBlock) -> str:
    return _WHITESPACE_RUN_RE.sub(" ", " ".join(line.text for line in block.question_lines)).strip()
