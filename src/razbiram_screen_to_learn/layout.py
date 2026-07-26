"""Geometry: what the page says, and where it says it.

``ocr.py`` returns text. That is enough only when the material marks its own structure with
letters ("A)", "B)"). A great deal of real material does not: an online quiz marks options with a
widget, a photographed page marks a question by making it bigger. For those, position and size
*are* the structure, so this module keeps them.

Tesseract's TSV output is the source: one row per word with a bounding box and a confidence.
Words are grouped back into lines, and lines carry the numbers a strategy needs to reason about
role (a heading is taller) and continuation (a wrapped line starts further left).

Nothing here decides what a line *means*. That is ``strategies.py``, so a new kind of document
becomes a new strategy rather than another branch in a parser.
"""

from __future__ import annotations

import csv
import io
import statistics
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from razbiram_screen_to_learn.ocr import available_models, run_tesseract

#: Below this, tesseract is guessing at noise. Widget chrome scores far under it.
MIN_WORD_CONFIDENCE = 30.0


@dataclass(frozen=True)
class Box:
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def overlaps_vertically(self, other: Box, *, min_fraction: float = 0.5) -> bool:
        """True when this box shares at least ``min_fraction`` of its height with ``other``."""
        overlap = min(self.bottom, other.bottom) - max(self.top, other.top)
        return overlap > 0 and overlap >= min_fraction * min(self.height, other.height)


@dataclass(frozen=True)
class Word:
    text: str
    box: Box
    confidence: float


@dataclass(frozen=True)
class Line:
    """One recognised line of text with the geometry a strategy can reason about."""

    text: str
    words: tuple[Word, ...]
    box: Box
    #: Median glyph height — the usable proxy for font size, robust to one tall letter.
    size: float
    confidence: float

    @property
    def left(self) -> int:
        return self.box.left

    @property
    def top(self) -> int:
        return self.box.top


def words_from_tsv(tsv: str, *, min_confidence: float = MIN_WORD_CONFIDENCE) -> list[list[Word]]:
    """Parse tesseract TSV into words, grouped by the line tesseract assigned them to.

    ``QUOTE_NONE`` matters: recognised text legitimately contains quote characters, and letting
    csv treat them as quoting silently swallows words.
    """
    grouped: OrderedDict[tuple[int, int, int, int], list[Word]] = OrderedDict()
    reader = csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE)
    for row in reader:
        if row.get("level") != "5":
            continue
        text = (row.get("text") or "").strip()
        if not text:
            continue
        try:
            confidence = float(row["conf"])
            box = Box(
                left=int(row["left"]),
                top=int(row["top"]),
                width=int(row["width"]),
                height=int(row["height"]),
            )
            key = (
                int(row["page_num"]),
                int(row["block_num"]),
                int(row["par_num"]),
                int(row["line_num"]),
            )
        except (KeyError, ValueError):
            continue
        if confidence < min_confidence:
            continue
        grouped.setdefault(key, []).append(Word(text=text, box=box, confidence=confidence))
    return [words for words in grouped.values() if words]


def to_lines(groups: list[list[Word]]) -> list[Line]:
    """Assemble word groups into lines, ordered down the page."""
    lines: list[Line] = []
    for words in groups:
        ordered = tuple(sorted(words, key=lambda w: w.box.left))
        left = min(w.box.left for w in ordered)
        top = min(w.box.top for w in ordered)
        right = max(w.box.right for w in ordered)
        bottom = max(w.box.bottom for w in ordered)
        lines.append(
            Line(
                text=" ".join(w.text for w in ordered),
                words=ordered,
                box=Box(left=left, top=top, width=right - left, height=bottom - top),
                size=statistics.median([w.box.height for w in ordered]),
                confidence=statistics.mean([w.confidence for w in ordered]),
            )
        )
    lines.sort(key=lambda line: (line.top, line.left))
    return lines


def read_lines(
    data: bytes,
    suffix: str,
    *,
    psm: int = 6,
    models: str | None = None,
    min_confidence: float = MIN_WORD_CONFIDENCE,
) -> list[Line]:
    """OCR ``data`` and return its lines with geometry.

    Lower ``min_confidence`` when the *unreadable* parts carry meaning: a checkbox or toggle is not
    text, so tesseract scores it poorly, and dropping it would discard the very marker that tells
    a caller where one answer choice ends and the next begins.
    """
    resolved = models or "+".join(available_models()) or "eng"
    with tempfile.TemporaryDirectory() as tmp:
        image = Path(tmp) / f"page{suffix or '.png'}"
        image.write_bytes(data)
        tsv = run_tesseract(image, resolved, psm, output="tsv")
        return to_lines(words_from_tsv(tsv, min_confidence=min_confidence))


def size_clusters(lines: list[Line], *, gap: float = 1.25) -> list[float]:
    """The distinct type sizes on the page, largest first.

    Sizes are grouped greedily: a new cluster starts where the next size is more than ``gap``
    times smaller than the current one. Typography that separates a heading from body text clears
    that easily; noise around a single size does not, so a uniform page yields one cluster.
    """
    sizes = sorted((line.size for line in lines), reverse=True)
    if not sizes:
        return []
    clusters: list[list[float]] = [[sizes[0]]]
    for size in sizes[1:]:
        if size <= 0:
            continue
        if statistics.median(clusters[-1]) > size * gap:
            clusters.append([size])
        else:
            clusters[-1].append(size)
    return [statistics.median(c) for c in clusters]
