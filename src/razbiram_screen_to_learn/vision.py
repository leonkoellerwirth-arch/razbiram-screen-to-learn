"""Read a page with a local vision model, when one is installed.

Tesseract recognises glyphs; it does not read pages. On this repo's own fixture it drops the
leading digit of question 2, and a question whose number is gone claims its neighbour's — so the
key row ``2. A, C`` binds elsewhere and the metals card exports one correct option instead of two,
silently. No post-processing recovers a digit that was never recognised. A vision-OCR model reads
the same page in one pass with the numbering intact.

**It reads; it does not structure.** The text it returns goes through the same ``textseg`` /
``textcards`` path as tesseract's, so answer binding, tiers and evidence are unchanged. A printed
key the model transcribes is evidence. An answer the model reasons out is not — and the prompt
here gives it no opening to offer one, which is why it asks for a transcript rather than for cards.

This does not overturn BIBLE 2026-07-26 ("a local LLM is a fallback, never the structurer"). That
was measured on *text* models restructuring OCR output — ``aya-expanse:8b`` dropped the last option
of every question, ``llama3.2`` split wrapped options apart — and it still holds for that job. This
is a different class of model doing the reading itself, and it enters through the same seam as any
other reader: one candidate reading among several, scored in ``pipeline.process_image``.

The model is reached over loopback ollama, so the tool stays local. Without ollama, without a known
model, or on any failure, this returns "" and the tesseract readings decide alone — installing a
model is an upgrade, never a requirement.
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.request
from contextlib import suppress
from functools import cache

from razbiram_screen_to_learn.progress import (
    STAGE_READING,
    ProgressEvent,
    ProgressFn,
    report,
)

#: Asked in this order. Dedicated OCR models first: they are trained to transcribe a page and
#: nothing else, which is exactly the contract here. The general vision models are listed after
#: because they will happily answer a question the page merely asked.
PREFERRED_MODELS: tuple[str, ...] = (
    "glm-ocr",
    "paddleocr-vl",
    "deepseek-ocr",
    "dots.ocr",
    "lightonocr",
    "qwen3-vl",
    "qwen2.5vl",
)

#: Transcribe, do not interpret. Deliberately not a JSON schema: the moment the model is asked for
#: cards, it starts supplying answers the page never printed.
PROMPT = "OCR"

#: Asking which models exist must not stall an upload when nothing is listening.
DISCOVERY_TIMEOUT_S = 3.0

#: A page can legitimately take a while on CPU.
READ_TIMEOUT_S = 600.0

#: Taller than this many times its width, a capture is a scroll, not a view. A vision model resizes
#: what it is given to a fixed budget, so the taller the capture the smaller every glyph becomes.
#: Measured on a 2500x28662 practice assessment: read whole, the model returned "Select that one"
#: where the page prints "Select all that apply" — which would silently turn a multiple-select
#: question into a single-choice card — plus "Definition of Reedy" and "Name of the above". Read in
#: bands, the same model returned all three verbatim.
TALL_RATIO = 2.0

#: Target band height. 1850px was the measured-clean size on that capture; the point is not the
#: number but that a band is a page-sized thing, which is what these models were trained on.
BAND_HEIGHT = 1850

#: How far a cut may move to land on a blank row instead of inside a question. Cutting at
#: background rather than overlapping bands means no text is transcribed twice, so nothing
#: downstream has to guess which of two readings of the same line to keep.
SEEK_ROWS = 600

#: Sampled columns per row, and the per-channel spread a row may have and still count as blank.
ROW_SAMPLES = 64
BLANK_TOLERANCE = 10

_FENCE_RE = re.compile(r"^```[a-z]*\n?|\n?```$")


def endpoint() -> str:
    """The loopback ollama base URL, honouring ollama's own ``OLLAMA_HOST`` convention."""
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").strip() or "127.0.0.1:11434"
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"
    return host.rstrip("/")


def _list_tags() -> set[str]:
    """Every model tag ollama reports, or an empty set when nothing is listening."""
    try:
        with urllib.request.urlopen(f"{endpoint()}/api/tags", timeout=DISCOVERY_TIMEOUT_S) as body:
            payload = json.load(body)
    except (OSError, ValueError):
        return set()
    return {str(entry.get("name", "")) for entry in payload.get("models", []) if entry}


@cache
def installed_model() -> str | None:
    """The first preferred model this machine actually has, or ``None``.

    Only the models named above are used. An arbitrary tag is not a reader — a general chat model
    handed an image either refuses or narrates it, and both outcomes are worse than no reading.

    Cached for the same reason ``ocr.available_models`` is: asking costs a request that every
    upload would otherwise pay, and pulling a model mid-session is rare enough that a restart is
    the right price.
    """
    tags = _list_tags()
    bare = {tag.split(":", 1)[0] for tag in tags}
    for candidate in PREFERRED_MODELS:
        if candidate in tags or candidate in bare:
            return candidate
    return None


def is_blank_row(image, y: int) -> bool:
    """Whether row ``y`` is one flat colour across the width — background, not content."""
    width = image.width
    step = max(1, width // ROW_SAMPLES)
    columns = range(0, width, step)
    for channel in range(3):
        values = [image.getpixel((x, y))[channel] for x in columns]
        if max(values) - min(values) > BLANK_TOLERANCE:
            return False
    return True


def band_bounds(image) -> list[tuple[int, int]]:
    """Where to cut a capture into page-sized bands, as ``(top, bottom)`` pairs.

    A short image yields one band, which is the whole image and the same call as before. A tall one
    is cut at background rows near each target height, so a question is never split across two
    reads. When no blank row is within reach the cut falls at the target anyway: a band that starts
    mid-question still reads its remaining lines correctly, and the segmenter downstream is built
    for text that begins in the middle of something.
    """
    width, height = image.size
    if height <= BAND_HEIGHT or height < width * TALL_RATIO:
        return [(0, height)]

    bounds: list[tuple[int, int]] = []
    top = 0
    while height - top > BAND_HEIGHT:
        target = top + BAND_HEIGHT
        cut = target
        for offset in range(SEEK_ROWS):
            for candidate in (target - offset, target + offset):
                if top < candidate < height and is_blank_row(image, candidate):
                    cut = candidate
                    break
            else:
                continue
            break
        bounds.append((top, cut))
        top = cut
    bounds.append((top, height))
    return bounds


def _bands(data: bytes) -> list[bytes]:
    """``data`` split into page-sized PNGs, or ``[data]`` when it needs no splitting."""
    from io import BytesIO

    from PIL import Image

    image = Image.open(BytesIO(data)).convert("RGB")
    bounds = band_bounds(image)
    if len(bounds) == 1:
        return [data]
    bands = []
    for top, bottom in bounds:
        buffer = BytesIO()
        image.crop((0, top, image.width, bottom)).save(buffer, format="PNG")
        bands.append(buffer.getvalue())
    return bands


def recognize_image(data: bytes, *, on_progress: ProgressFn | None = None) -> str:
    """Transcribe ``data``, or return "" when no model is available or the call fails.

    A tall capture is read in bands and the transcripts joined, because a scroll read whole comes
    back subtly wrong rather than obviously empty — see ``TALL_RATIO``.

    Failure is silent by contract: this is one reading among several, and losing it must cost
    nothing but itself. A band that fails contributes nothing and the rest still read.
    """
    model = installed_model()
    if model is None:
        return ""

    bands = [data]
    with suppress(Exception):
        # Without Pillow, or on anything unreadable, the whole image is the single band.
        bands = _bands(data)

    transcripts = []
    for index, band in enumerate(bands, start=1):
        report(
            on_progress,
            ProgressEvent(
                stage=STAGE_READING,
                detail=f"Reading with {model}"
                + (f" (band {index} of {len(bands)})" if len(bands) > 1 else ""),
                index=index,
                total=len(bands),
            ),
        )
        transcripts.append(_transcribe(band, model))
    return "\n\n".join(part for part in transcripts if part)


def _transcribe(data: bytes, model: str) -> str:
    """One call to the model. Returns "" on any failure, so one bad band never loses the rest.

    ``temperature`` is pinned to 0 so the same page reads the same way twice — identifiers
    downstream are derived from content and may not drift between runs.
    """
    request = urllib.request.Request(
        f"{endpoint()}/api/chat",
        data=json.dumps(
            {
                "model": model,
                "stream": False,
                "messages": [
                    {
                        "role": "user",
                        "content": PROMPT,
                        "images": [base64.b64encode(data).decode()],
                    }
                ],
                "options": {"temperature": 0},
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=READ_TIMEOUT_S) as body:
            payload = json.load(body)
    except (OSError, ValueError):
        return ""
    content = str((payload.get("message") or {}).get("content", "")).strip()
    return _FENCE_RE.sub("", content).strip()
