"""Read text out of an image.

Parsing is the pipeline's job, not this module's — this returns raw recognised text, so the same
text path serves screenshots, photos, PDFs and pasted text alike.

There is deliberately **no user-facing language choice**. This tool turns material into cards; it
is not a language product. Tesseract loads several models at once (``-l eng+bul+…``), so mixed
Latin/Cyrillic exam material is read without asking anyone to classify their own file first. Which
models exist on the machine is an implementation detail, resolved at call time.

Requires the ``tesseract`` binary (brew install tesseract tesseract-lang). It is invoked as a
subprocess rather than through a binding so the dependency stays optional and inspectable.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from razbiram_screen_to_learn.progress import (
    STAGE_READING,
    ProgressEvent,
    ProgressFn,
    report,
)

#: Extensions leptonica reads. HEIC is absent on purpose — it needs a converter we do not ship.
IMAGE_SUFFIXES: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".gif", ".pnm", ".ppm"}
)

#: Tried in order; every one present on the machine is loaded together. Latin and Cyrillic first
#: because that is the corpus, but nothing here branches on the document's actual language.
PREFERRED_MODELS: tuple[str, ...] = ("eng", "bul", "deu", "rus")

#: Page-segmentation modes, cheapest-first. 3 is tesseract's own default (full auto). A screenshot
#: of a quiz usually needs 6 (one uniform block) and a photographed page 4 (single column).
PSM_LADDER: tuple[int, ...] = (3, 6, 4)


class OcrUnavailable(RuntimeError):
    """The tesseract binary is not installed."""


@dataclass(frozen=True)
class OcrResult:
    text: str
    #: Which models were actually loaded, e.g. "eng+bul".
    models: str
    #: The page-segmentation mode that produced ``text``.
    psm: int


def tesseract_path() -> str | None:
    return shutil.which("tesseract")


@cache
def available_models() -> list[str]:
    """The preferred models this machine actually has, in preference order.

    Cached: the installed model set does not change while the process runs, and asking costs a
    full tesseract start-up — a tax every upload would otherwise pay. Installing a language pack
    therefore needs a restart to take effect, which is the right trade for a local tool.
    """
    binary = tesseract_path()
    if binary is None:
        return []
    try:
        proc = subprocess.run(
            [binary, "--list-langs"], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return []
    installed = {line.strip() for line in proc.stdout.splitlines() if line.strip()}
    return [model for model in PREFERRED_MODELS if model in installed]


def run_tesseract(image: Path, models: str, psm: int, *, output: str = "txt") -> str:
    """Invoke tesseract once and return its stdout, or "" if it failed.

    The single place the binary is called. ``layout.py`` asks for ``tsv`` and this module for plain
    text; keeping one invocation means the timeout, the argument order and the failure convention
    cannot drift apart between them.
    """
    binary = tesseract_path()
    if binary is None:
        raise OcrUnavailable(
            "the 'tesseract' binary was not found; install it with: "
            "brew install tesseract tesseract-lang"
        )
    args = [binary, str(image), "stdout", "-l", models, "--psm", str(psm)]
    if output != "txt":
        args.append(output)
    proc = subprocess.run(args, capture_output=True, text=True, timeout=600, check=False)
    return proc.stdout if proc.returncode == 0 else ""


def recognize_image(
    data: bytes,
    suffix: str,
    *,
    accept: Callable[[str], bool] | None = None,
    on_progress: ProgressFn | None = None,
) -> OcrResult:
    """Recognise ``data`` and return the best text found.

    ``accept`` is an optional predicate over the recognised text. When given, the page-segmentation
    ladder stops at the first mode whose output it accepts — that is how the caller can say "keep
    trying until this parses into questions" without this module knowing what a question is.
    """
    binary = tesseract_path()
    if binary is None:
        raise OcrUnavailable(
            "the 'tesseract' binary was not found; install it with: "
            "brew install tesseract tesseract-lang"
        )

    models = "+".join(available_models()) or "eng"

    with tempfile.TemporaryDirectory() as tmp:
        image = Path(tmp) / f"upload{suffix or '.png'}"
        image.write_bytes(data)

        best = OcrResult(text="", models=models, psm=PSM_LADDER[0])
        for position, psm in enumerate(PSM_LADDER, start=1):
            report(
                on_progress,
                ProgressEvent(
                    stage=STAGE_READING,
                    detail=f"Reading the image (attempt {position} of up to {len(PSM_LADDER)})",
                    index=position,
                    total=len(PSM_LADDER),
                ),
            )
            text = run_tesseract(image, models, psm)
            candidate = OcrResult(text=text, models=models, psm=psm)
            if accept is not None and accept(text):
                return candidate
            # Without a predicate, or while none satisfies it, keep the wordiest result.
            if len(text.split()) > len(best.text.split()):
                best = candidate
        return best
