"""Loopback API for the local studio.

M0 spike. It binds to loopback only and holds no state between requests: a dropped file is
processed and the result returned. The session/artifact store, job queue and pairing endpoints in
``docs/architecture/REPOSITORY_BLUEPRINT.md`` arrive with M1, and the paired extension transport
with M2E.

No telemetry, no outbound network, no account. Captured content never leaves the machine.
"""

from __future__ import annotations

import webbrowser
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from razbiram_screen_to_learn import __version__
from razbiram_screen_to_learn.contracts import dump_document
from razbiram_screen_to_learn.pipeline import process_markup


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
ALLOWED_SUFFIXES = {".html", ".htm", ".txt"}


def create_app() -> FastAPI:
    app = FastAPI(title="razbiram-screen-to-learn studio", version=__version__)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.post("/v1/process")
    async def process(file: UploadFile) -> dict:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise HTTPException(
                status_code=400,
                detail=f"unsupported file type {suffix or '(none)'}; accepted: "
                + ", ".join(sorted(ALLOWED_SUFFIXES)),
            )
        raw = await file.read()
        if len(raw) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"file is {len(raw)} bytes; the limit is {MAX_UPLOAD_BYTES}",
            )
        try:
            markup = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="file is not valid UTF-8") from exc

        result = process_markup(markup)
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

    if STATIC_DIR is not None:
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

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
