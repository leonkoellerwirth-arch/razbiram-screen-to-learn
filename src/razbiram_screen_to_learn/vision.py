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


def recognize_image(data: bytes, *, on_progress: ProgressFn | None = None) -> str:
    """Transcribe ``data``, or return "" when no model is available or the call fails.

    Failure is silent by contract: this is one reading among several, and losing it must cost
    nothing but itself. ``temperature`` is pinned to 0 so the same page reads the same way twice —
    identifiers downstream are derived from content and may not drift between runs.
    """
    model = installed_model()
    if model is None:
        return ""
    report(
        on_progress,
        ProgressEvent(stage=STAGE_READING, detail=f"Reading the image with {model}"),
    )
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
