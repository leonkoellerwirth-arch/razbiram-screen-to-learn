"""Honest progress reporting.

A stage reports only what it actually knows. Where a count exists it is given; where none exists
the stage says so rather than inventing a percentage, because a bar that fills at a made-up rate
teaches a user to distrust every bar afterwards.

``total`` is an **upper bound**, not a promise: the OCR ladder stops as soon as a pass yields
usable text, so "pass 1 of up to 3" is the truthful phrasing and finishing early is a success, not
a jump in the bar.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass

#: Stage identifiers. Deliberately coarse — a stage exists here only if a user would notice it
#: taking time, and each one is named for what is happening, not for the function that runs.
Stage = str

STAGE_RECEIVING = "receiving"
STAGE_READING = "reading"
STAGE_SEGMENTING = "segmenting"
STAGE_VALIDATING = "validating"
STAGE_EXPORTING = "exporting"


@dataclass(frozen=True)
class ProgressEvent:
    """One observation about work in flight."""

    stage: Stage
    #: Human-facing sentence. The server owns the wording so every client says the same thing.
    detail: str
    #: 1-based position within ``total``, when the stage is countable.
    index: int | None = None
    #: Upper bound for ``index``. May be reached early — see the module docstring.
    total: int | None = None

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"stage": self.stage, "detail": self.detail}
        if self.index is not None:
            payload["index"] = self.index
        if self.total is not None:
            payload["total"] = self.total
        return payload


#: Sinks are optional everywhere. A pipeline must run identically when nobody is watching.
ProgressFn = Callable[[ProgressEvent], None]


def report(sink: ProgressFn | None, event: ProgressEvent) -> None:
    """Deliver ``event`` when someone is listening.

    A failing sink must never break the work it is describing: progress is commentary, and a
    disconnected client is a normal event, not an error in the pipeline.
    """
    if sink is None:
        return
    with suppress(Exception):
        sink(event)
