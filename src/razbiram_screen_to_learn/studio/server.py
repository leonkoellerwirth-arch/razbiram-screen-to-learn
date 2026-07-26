"""Loopback API for the local studio.

M0 spike. It binds to loopback only and holds no state between requests: a dropped file is
processed and the result returned. The session/artifact store, job queue and pairing endpoints in
``docs/architecture/REPOSITORY_BLUEPRINT.md`` arrive with M1, and the paired extension transport
with M2E.

No telemetry, no outbound network, no account. Captured content never leaves the machine.
"""

from __future__ import annotations

import asyncio
import json
import threading
import webbrowser
from collections.abc import AsyncIterator
from pathlib import Path
from queue import Queue

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from razbiram_screen_to_learn import __version__
from razbiram_screen_to_learn.contracts import dump_document
from razbiram_screen_to_learn.ocr import IMAGE_SUFFIXES, OcrUnavailable
from razbiram_screen_to_learn.pipeline import (
    PipelineResult,
    process_image,
    process_markup,
    process_text,
)
from razbiram_screen_to_learn.progress import ProgressEvent, ProgressFn
from razbiram_screen_to_learn.textseg import segment


def _reads_as_questions(text: str) -> bool:
    """Whether a page-segmentation attempt produced anything worth keeping.

    Used to stop the OCR ladder early: the first mode that yields a question with real options
    wins, so a clean screenshot costs one pass and only a hard photo pays for three.
    """
    blocks, _ = segment(text)
    return any(len(block.option_lines) >= 2 for block in blocks)


def _static_dir() -> Path | None:
    """Where the built studio lives.

    Packaged installs carry it inside the package; a source checkout has it under
    ``apps/studio/dist`` after ``npm run build``. Returning ``None`` is a valid state — the API
    still serves, and ``serve()`` says so rather than presenting a blank page.
    """
    packaged = Path(__file__).resolve().parent / "static"
    if packaged.is_dir():
        return packaged
    repo_root = Path(__file__).resolve().parents[3]
    built = repo_root / "apps" / "studio" / "dist"
    return built if built.is_dir() else None


STATIC_DIR = _static_dir()

#: Intake is bounded on purpose; SOLUTION_ARCHITECTURE.md sets explicit limits per artifact.
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MARKUP_SUFFIXES = {".html", ".htm"}
TEXT_SUFFIXES = {".txt", ".md"}
ALLOWED_SUFFIXES = MARKUP_SUFFIXES | TEXT_SUFFIXES | IMAGE_SUFFIXES


def _run_pipeline(
    filename: str, raw: bytes, on_progress: ProgressFn | None = None
) -> PipelineResult:
    """Route one upload to the right intake path. Raises HTTPException for anything a caller did.

    Shared by the plain and the streaming endpoint so the two can never diverge on what is
    accepted, how it is read, or what a failure means.
    """
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported file type {suffix or '(none)'}; accepted: "
            + ", ".join(sorted(ALLOWED_SUFFIXES)),
        )
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"file is {len(raw)} bytes; the limit is {MAX_UPLOAD_BYTES}",
        )

    title = Path(filename or "Captured deck").stem or "Captured deck"

    if suffix in IMAGE_SUFFIXES:
        # An image carries no DOM, so evidence must come from the picture — which invariant 2
        # allows precisely because there is nothing better to prefer. `process_image` reads it
        # both ways (letters, and drawn structure) and keeps whichever yields more answerable
        # questions.
        try:
            result = process_image(raw, suffix, title=title, on_progress=on_progress)
        except OcrUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if not result.document.cards and not (result.text or "").strip():
            raise HTTPException(status_code=422, detail="no text could be read from this image")
        return result

    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="file is not valid UTF-8") from exc

    if suffix in MARKUP_SUFFIXES:
        return process_markup(decoded)
    # Not "reviewer": nobody confirmed this. The text was machine-parsed exactly as an OCR result
    # is, so it carries the same evidence kind and the same burden of proof.
    return process_text(
        decoded,
        title=title,
        source_kind="text-input",
        evidence_kind="ocr",
        on_progress=on_progress,
    )


def _payload(result: PipelineResult) -> dict:
    return {
        "captureIr": dump_document(result.document),
        "issues": [
            {
                "code": issue.code,
                "message": issue.message,
                "blocking": issue.blocking,
                "cardId": issue.card_id,
            }
            for issue in result.issues
        ],
        "export": {
            "deck": result.export.deck,
            "blockedCardIds": result.export.blocked_card_ids,
            "blocked": [
                {"cardId": b.card_id, "family": b.family, "reason": b.reason}
                for b in result.export.blocked
            ],
        },
        "unsupported": result.unsupported,
    }


async def _stream_pipeline(filename: str, raw: bytes) -> AsyncIterator[str]:
    """Run the pipeline on a worker thread and emit its progress as newline-delimited JSON.

    The pipeline is synchronous and CPU-bound (tesseract), so it cannot yield to the event loop on
    its own. Running it on a thread and draining a queue is what lets the browser hear about a
    sixty-second read while it is happening instead of after it.
    """
    queue: Queue[tuple[str, dict] | None] = Queue()

    def sink(event: ProgressEvent) -> None:
        queue.put(("progress", event.as_dict()))

    def work() -> None:
        try:
            queue.put(("result", _payload(_run_pipeline(filename, raw, sink))))
        except HTTPException as exc:
            queue.put(("error", {"detail": str(exc.detail), "status": exc.status_code}))
        except Exception as exc:
            queue.put(("error", {"detail": f"{type(exc).__name__}: {exc}", "status": 500}))
        finally:
            queue.put(None)

    threading.Thread(target=work, daemon=True).start()

    loop = asyncio.get_running_loop()
    while True:
        item = await loop.run_in_executor(None, queue.get)
        if item is None:
            return
        kind, body = item
        yield json.dumps({"event": kind, **body}) + "\n"


def create_app() -> FastAPI:
    app = FastAPI(title="razbiram-screen-to-learn studio", version=__version__)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.post("/v1/process")
    async def process(file: UploadFile) -> dict:
        return _payload(_run_pipeline(file.filename or "", await file.read()))

    @app.post("/v1/process/stream")
    async def process_stream(file: UploadFile) -> StreamingResponse:
        """Same work as /v1/process, narrating itself as it goes.

        Errors arrive as a final `error` event rather than an HTTP status, because the response
        has already begun by the time most of them can happen.
        """
        return StreamingResponse(
            _stream_pipeline(file.filename or "", await file.read()),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    if STATIC_DIR is not None and (STATIC_DIR / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    if STATIC_DIR is not None and (STATIC_DIR / "index.html").is_file():

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(STATIC_DIR / "index.html")

    return app


def serve(*, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> int:
    import uvicorn

    url = f"http://{host}:{port}/"
    print(f"Studio on {url}  (loopback only, no telemetry)")
    if STATIC_DIR is None:
        print("note: the UI is not built. Run: (cd apps/studio && npm ci && npm run build)")
        print("      the API is available regardless.")
    if open_browser:
        webbrowser.open(url)
    uvicorn.run(create_app(), host=host, port=port, log_level="info")
    return 0
