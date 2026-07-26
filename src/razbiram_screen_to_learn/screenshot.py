"""Reading a quiz whose structure is drawn, not written.

``textseg.py`` needs the material to mark itself: "A)", "B)", a trailing "Answers:" block. A great
deal of real material marks nothing. An online practice quiz makes the question bigger, puts a
widget in front of each choice, and tints the row it considers correct — carrying in typography,
geometry and colour exactly what a printed sheet carries in letters.

This module reads those three signals and produces the same ``RawBlock`` values ``textseg`` does,
so family detection, answer binding and card construction stay in one place downstream.

Three findings shape it, each measured rather than assumed:

1. **Type size separates the roles.** A question, a choice and the explanation beneath them sit in
   distinct size clusters, and which cluster is which follows from their order, not from a number
   baked in here.
2. **A choice begins with an unreadable token.** The widget is not text, so tesseract returns a
   short, low-confidence guess at it. Indentation alone does not separate a choice from a wrapped
   continuation — the two overlap — but that leading token does, cleanly.
3. **Tinted rows defeat tesseract's layout analysis.** A row inside a coloured, bordered box is
   frequently dropped whole; cropping it away from its own chrome recovers it. Since the tint is
   what marks the correct answer, the rows most likely to vanish are the ones that matter most.

Correctness read here is *measured* — a row is correct because its background differs from the
page, which is evidence, not inference. Nothing in this module guesses an answer.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass

from razbiram_screen_to_learn.layout import Box, Line, read_lines, size_clusters
from razbiram_screen_to_learn.textseg import AnswerKey, ParsedLine, RawBlock

#: A leading token no longer than this, recognised with less confidence than body text, is read as
#: a widget rather than a word. Body text on the sampled material sits at 95+; widgets at 58-90.
WIDGET_MAX_CHARS = 2
WIDGET_MAX_CONFIDENCE = 92.0

#: How far a row's mean colour must lean towards one channel before it counts as deliberate
#: emphasis. Neutral page chrome measures within a point or two of zero; a tinted fill measures
#: around ten, its border far more.
TINT_THRESHOLD = 6.0

#: Ignore emphasis runs shorter than this many pixels — antialiasing and rules are not highlights.
MIN_BAND_HEIGHT = 12

#: Below this mean confidence a line is smear, not text. Body text on the sampled material sits at
#: 94-96 and genuine option lines at 68-90, so the floor is far from anything real.
MIN_LINE_CONFIDENCE = 40.0

#: A line must contain at least one letter run this long to count as carrying words.
MIN_WORD_RUN = 3
WORD_RUN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


@dataclass(frozen=True)
class Band:
    """A vertical run of rows whose background departs from the page's own."""

    top: int
    bottom: int
    #: Which channel the run leans towards: 0 red, 1 green, 2 blue.
    channel: int

    def contains(self, box: Box) -> bool:
        centre = box.top + box.height / 2
        return self.top <= centre <= self.bottom


def is_content(line: Line) -> bool:
    """Whether a line carries text, as opposed to the drawing around it.

    Table rules and cell borders survive OCR as plausible-looking strings, so neither measure
    settles it alone: a border reads at a confidence indistinguishable from a real answer, and a
    smeared run of letters can score near zero while looking like prose. Together they separate
    cleanly — chrome is either **unreadable** or **wordless**.
    """
    if line.confidence < MIN_LINE_CONFIDENCE:
        return False
    return any(len(run) >= MIN_WORD_RUN for run in WORD_RUN_RE.findall(line.text))


def _is_widget(line: Line) -> bool:
    """Whether this line opens with something tesseract could not read as a word."""
    if not line.words:
        return False
    first = line.words[0]
    return len(first.text) <= WIDGET_MAX_CHARS and first.confidence < WIDGET_MAX_CONFIDENCE


def _role_sizes(lines: list[Line]) -> tuple[float, float]:
    """The type sizes that stand for "question" and "choice" on this page.

    Read from the material rather than fixed here, and chosen by **how much text is set in them**
    rather than by which is largest. A page carries stray oversized fragments — a banner, a
    mis-measured line — and ranking by size alone picks those and misses the body entirely. The
    two sizes most of the page is written in are the question and the choice; the larger is the
    question.

    A page with only one populated size returns it twice, which tells the caller there is no
    typographic hierarchy here and this strategy has nothing to work from.
    """
    clusters = size_clusters(lines)
    if not clusters:
        return 0.0, 0.0

    def nearest(size: float) -> float:
        return min(clusters, key=lambda c: abs(c - size))

    weight: dict[float, int] = {}
    for line in lines:
        if line.size > 0:
            cluster = nearest(line.size)
            weight[cluster] = weight.get(cluster, 0) + 1

    dominant = sorted(weight, key=lambda c: (-weight[c], -c))[:2]
    if len(dominant) < 2:
        only = dominant[0] if dominant else 0.0
        return only, only
    return max(dominant), min(dominant)


def _tint(pixels: list[tuple[int, int, int]]) -> tuple[float, int]:
    """How far a row leans away from grey, and which channel it leans towards.

    The channel matters as much as the amount. A results page marks correct answers in one colour
    and wrong ones in another; a detector that only measured "not grey" would mark both, which is
    worse than marking nothing.
    """
    if not pixels:
        return 0.0, -1
    means = [statistics.mean(p[i] for p in pixels) for i in range(3)]
    leans = [means[i] - (sum(means) - means[i]) / 2 for i in range(3)]
    channel = max(range(3), key=lambda i: leans[i])
    return leans[channel], channel


def emphasis_bands(image, left: int, right: int, *, step: int = 4) -> list[Band]:
    """Find vertical runs whose background is deliberately tinted.

    Sampled every ``step`` rows across the content column only: page margins carry their own
    chrome and would drown the signal.
    """
    width, height = image.size
    left = max(0, min(left, width - 1))
    right = max(left + 1, min(right, width))

    bands: list[Band] = []
    run_start: int | None = None
    run_channel = -1
    for y in range(0, height, step):
        row = list(image.crop((left, y, right, min(y + 1, height))).getdata())
        amount, channel = _tint(row)
        tinted = amount >= TINT_THRESHOLD
        # A change of channel ends the run: adjacent blocks in different colours are two marks,
        # not one.
        if tinted and (run_start is None or channel != run_channel):
            if run_start is not None and y - run_start >= MIN_BAND_HEIGHT:
                bands.append(Band(top=run_start, bottom=y, channel=run_channel))
            run_start, run_channel = y, channel
        elif not tinted and run_start is not None:
            if y - run_start >= MIN_BAND_HEIGHT:
                bands.append(Band(top=run_start, bottom=y, channel=run_channel))
            run_start = None
    if run_start is not None and height - run_start >= MIN_BAND_HEIGHT:
        bands.append(Band(top=run_start, bottom=height, channel=run_channel))
    return bands


def marking_bands(bands: list[Band], options: list[Line]) -> list[Band]:
    """Keep only the bands that plausibly mark an answer.

    Two filters, neither of which needs to know what colour "correct" is:

    * A band must sit on an answer. Page banners and section fills are tinted too, and they are
      not marks.
    * Where a page marks in more than one colour — a results view showing right *and* wrong — the
      **more common** colour is the one that means correct. Every question has a right answer and
      therefore carries that mark; only the questions the reader got wrong carry the other. The
      counts settle it, and when they tie nothing is returned, because guessing between the two
      would teach someone the wrong answer.
    """
    on_answers = [b for b in bands if any(b.contains(line.box) for line in options)]
    if not on_answers:
        return []

    per_channel: dict[int, int] = {}
    for band in on_answers:
        per_channel[band.channel] = per_channel.get(band.channel, 0) + 1
    if len(per_channel) == 1:
        return on_answers

    ranked = sorted(per_channel.items(), key=lambda kv: -kv[1])
    if ranked[0][1] == ranked[1][1]:
        return []
    return [b for b in on_answers if b.channel == ranked[0][0]]


def _parsed(line: Line, *, marked: bool, kind: str) -> ParsedLine:
    """Present a geometric line as the lexical one downstream already understands."""
    text = line.text
    if kind == "option" and _is_widget(line):
        # Drop the unreadable widget token; it is furniture, not part of the answer.
        text = " ".join(word.text for word in line.words[1:]).strip() or line.text
    # Some widgets OCR as two tokens ("@ |"); a lone separator left behind is still furniture.
    text = text.lstrip("|:. ").strip()
    return ParsedLine(n=line.top, raw=line.text, text=text, kind=kind, marked=marked)


def blocks_from_image(data: bytes, suffix: str) -> tuple[list[RawBlock], AnswerKey]:
    """Read an image into question blocks using typography, geometry and colour.

    Returns the blocks and an empty answer key: correctness here is carried per option (as an
    inline mark), never as a separate key section.
    """
    # Read with no confidence floor: the widget marking each choice is deliberately unreadable, and
    # discarding it would remove the very signal that separates one choice from the next. Chrome is
    # dropped afterwards by `is_content`, which can judge the whole line rather than one token.
    lines = [line for line in read_lines(data, suffix, min_confidence=0.0) if is_content(line)]
    if not lines:
        return [], {}

    question_size, choice_size = _role_sizes(lines)
    if question_size == choice_size:
        return [], {}  # no typographic hierarchy — this is not the material this strategy reads

    midpoint = (question_size + choice_size) / 2
    # Below the choice size sits commentary (explanations, footnotes); it is not an answer.
    floor = choice_size * 0.85

    bands: list[Band] = []
    try:
        from io import BytesIO

        from PIL import Image

        image = Image.open(BytesIO(data)).convert("RGB")
        column_left = int(statistics.median([line.left for line in lines]))
        column_right = int(statistics.median([line.box.right for line in lines]))
        bands = emphasis_bands(image, column_left, column_right)
    except Exception:
        bands = []

    option_lines = [line for line in lines if floor <= line.size < midpoint]
    marks = marking_bands(bands, option_lines)

    blocks: list[RawBlock] = []
    current: RawBlock | None = None
    index = 0

    for line in lines:
        if line.size < floor:
            continue  # explanation or footnote

        if line.size >= midpoint:
            if current is not None and current.option_lines:
                blocks.append(current)
                current = None
            if current is None:
                index += 1
                current = RawBlock(index=index, line_start=line.top, line_end=line.top)
            current.question_lines.append(_parsed(line, marked=False, kind="text"))
            current.line_end = line.top
            continue

        if current is None:
            index += 1
            current = RawBlock(index=index, line_start=line.top, line_end=line.top)

        if _is_widget(line) or not current.option_lines:
            marked = any(band.contains(line.box) for band in marks)
            current.option_lines.append(_parsed(line, marked=marked, kind="option"))
        else:
            # A wrapped continuation belongs to the choice above it.
            previous = current.option_lines[-1]
            joined = f"{previous.text} {line.text}".strip()
            current.option_lines[-1] = ParsedLine(
                n=previous.n,
                raw=previous.raw,
                text=joined,
                kind="option",
                marked=previous.marked,
            )
        current.line_end = line.top

    if current is not None and (current.option_lines or current.question_lines):
        blocks.append(current)

    return [_settle_marks(block) for block in blocks], {}


def _settle_marks(block: RawBlock) -> RawBlock:
    """Withdraw a block's marks when they cannot be distinguishing anything.

    Emphasis works by contrast, so a mark on most of a question's choices is not a mark — it is a
    coloured table, a shaded row group, or a misread. Rather than hand a learner a question with
    four right answers out of five, the marks are dropped and the card goes to review unbound.

    Half is deliberately allowed through: a true/false question marks one of two, and a
    multiple-select question legitimately marks two of four.
    """
    marked = [line for line in block.option_lines if line.marked]
    if not marked or len(marked) * 2 <= len(block.option_lines):
        return block
    block.option_lines = [
        ParsedLine(n=o.n, raw=o.raw, text=o.text, kind=o.kind, marked=False)
        for o in block.option_lines
    ]
    return block
