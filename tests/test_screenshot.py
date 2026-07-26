"""Reading structure that is drawn rather than written.

The decisions here were derived from measurements on real material, and each test pins one of
them so a later change has to argue with the evidence rather than with taste.
"""

from __future__ import annotations

from razbiram_screen_to_learn.layout import Box, Line, Word, size_clusters, to_lines, words_from_tsv
from razbiram_screen_to_learn.screenshot import (
    Band,
    _role_sizes,
    _settle_marks,
    is_content,
    marking_bands,
)
from razbiram_screen_to_learn.textseg import ParsedLine, RawBlock


def line(text: str, *, size: float = 30, conf: float = 95, top: int = 0, left: int = 0) -> Line:
    words = tuple(
        Word(
            text=part,
            box=Box(left=left + i * 40, top=top, width=38, height=int(size)),
            confidence=conf,
        )
        for i, part in enumerate(text.split())
    )
    return Line(
        text=text,
        words=words,
        box=Box(left=left, top=top, width=max(1, 40 * len(words)), height=int(size)),
        size=size,
        confidence=conf,
    )


# --- chrome versus content -------------------------------------------------------------------


def test_a_smeared_run_is_not_content_however_word_like() -> None:
    """Measured at confidence 0-3 on real material while reading as plausible letters."""
    assert not is_content(line("ровововосососососососесососососесосоносонине", conf=0.0))
    assert not is_content(line("Pewee e eee eee", conf=2.8))


def test_a_wordless_line_is_not_content_however_confident() -> None:
    """A cell border reads at confidence 82 — indistinguishable from a real answer by that alone."""
    assert not is_content(line("[| [|", conf=82.3))


def test_a_real_choice_survives_both_filters() -> None:
    assert is_content(line("В Definition of Ready", conf=87.8))
    assert is_content(line("ı @ | User Stories -", conf=83.3))


# --- typographic roles -----------------------------------------------------------------------


def test_roles_follow_where_the_text_is_not_which_size_is_largest() -> None:
    """A handful of oversized fragments must not outrank the body of the page.

    Taken from the sampled quiz: 103 lines of choices at 29, 50 of questions at 49, and a few
    stray lines measured at 62 that belong to neither.
    """
    lines = [line("choice", size=29) for _ in range(103)]
    lines += [line("question", size=49) for _ in range(50)]
    lines += [line("stray", size=62) for _ in range(3)]
    question, choice = _role_sizes(lines)
    assert question > choice
    assert round(choice) == 29
    assert round(question) == 49


def test_a_page_set_in_one_size_reports_no_hierarchy() -> None:
    lines = [line("uniform", size=30) for _ in range(20)]
    question, choice = _role_sizes(lines)
    assert question == choice


# --- which colour means correct --------------------------------------------------------------


def test_a_single_emphasis_colour_is_taken_as_the_mark() -> None:
    options = [line("choice", top=100)]
    bands = [Band(top=90, bottom=140, channel=1)]
    assert marking_bands(bands, options) == bands


def test_the_common_colour_wins_when_a_page_marks_right_and_wrong() -> None:
    """Every question carries the correct mark; only mistakes carry the other one."""
    options = [line("choice", top=100 * i) for i in range(6)]
    green = [Band(top=100 * i, bottom=100 * i + 30, channel=1) for i in range(4)]
    pink = [Band(top=100 * i, bottom=100 * i + 30, channel=0) for i in range(4, 6)]
    kept = marking_bands(green + pink, options)
    assert {band.channel for band in kept} == {1}
    assert len(kept) == 4


def test_two_equally_common_colours_bind_nothing() -> None:
    options = [line("choice", top=100 * i) for i in range(4)]
    bands = [
        Band(top=0, bottom=30, channel=1),
        Band(top=100, bottom=130, channel=1),
        Band(top=200, bottom=230, channel=0),
        Band(top=300, bottom=330, channel=0),
    ]
    assert marking_bands(bands, options) == []


def test_a_band_that_touches_no_answer_is_not_a_mark() -> None:
    """Page banners and section fills are tinted too."""
    options = [line("choice", top=5000)]
    assert marking_bands([Band(top=0, bottom=200, channel=1)], options) == []


# --- emphasis must distinguish ---------------------------------------------------------------


def marked_block(marks: list[bool]) -> RawBlock:
    return RawBlock(
        index=1,
        option_lines=[
            ParsedLine(n=i, raw="o", text=f"option {i}", kind="option", marked=m)
            for i, m in enumerate(marks)
        ],
    )


def test_marking_most_of_a_question_marks_nothing() -> None:
    """Four correct answers out of five is a coloured table, not an answer key."""
    settled = _settle_marks(marked_block([True, True, True, True, False]))
    assert not any(o.marked for o in settled.option_lines)


def test_half_the_options_may_legitimately_be_marked() -> None:
    """True/false marks one of two; multiple-select marks two of four."""
    assert sum(o.marked for o in _settle_marks(marked_block([True, False])).option_lines) == 1
    assert (
        sum(o.marked for o in _settle_marks(marked_block([True, True, False, False])).option_lines)
        == 2
    )


# --- geometry ---------------------------------------------------------------------------------


def test_words_are_grouped_into_the_lines_tesseract_assigned() -> None:
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t0\t0\t0\t0\t10\t10\t30\t20\t95\tHello\n"
        "5\t1\t0\t0\t0\t1\t50\t10\t30\t20\t93\tworld\n"
        "5\t1\t0\t0\t1\t0\t10\t40\t30\t20\t90\tSecond\n"
    )
    lines = to_lines(words_from_tsv(tsv))
    assert [line.text for line in lines] == ["Hello world", "Second"]


def test_a_quote_in_recognised_text_does_not_swallow_the_line() -> None:
    """csv quoting would eat the rest of the row; the parser must read it literally."""
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        '5\t1\t0\t0\t0\t0\t10\t10\t30\t20\t95\t"Done",\n'
        "5\t1\t0\t0\t0\t1\t50\t10\t30\t20\t95\tvaluable\n"
    )
    assert to_lines(words_from_tsv(tsv))[0].text == '"Done", valuable'


def test_size_clusters_separate_a_heading_from_body_text() -> None:
    lines = [line("body", size=29) for _ in range(10)] + [line("head", size=50) for _ in range(4)]
    assert [round(c) for c in size_clusters(lines)] == [50, 29]


def test_size_clusters_of_a_uniform_page_collapse_to_one() -> None:
    assert len(size_clusters([line("body", size=30) for _ in range(10)])) == 1
