"""Import explicitly captured Quizlet set payloads into the normal review/export pipeline.

This module deliberately does not fetch Quizlet. The repo's safety contract forbids hidden API
use and CAPTCHA bypass, so the boundary here is a file the user intentionally captured: the set
page HTML/``__NEXT_DATA__`` payload plus optional paginated API JSON payloads. From that point on,
Quizlet is just another structured source feeding Capture IR and the existing exporter.
"""

from __future__ import annotations

import hashlib
import html
import importlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from razbiram_screen_to_learn.contracts import (
    CaptureIR,
    Card,
    Deck,
    Evidence,
    Field_,
    Review,
    Rights,
    Source,
    Target,
)
from razbiram_screen_to_learn.export import TARGET_PROFILE, export_deck
from razbiram_screen_to_learn.identity import (
    capture_id,
    card_id,
    clean_text,
    question_fingerprint,
    source_id,
)
from razbiram_screen_to_learn.pipeline import LIVE_CAPABILITIES, PipelineResult
from razbiram_screen_to_learn.validators import validate_for_export

_NEXT_DATA = re.compile(
    r'<script id=["\']__NEXT_DATA__["\'] type=["\']application/json["\']>(.*?)</script>',
    re.DOTALL,
)
_CAPTURE_MARKER = '<script id="__QUIZLET_CAPTURE_STATUS__" type="application/json">'


@dataclass(frozen=True)
class QuizletItem:
    item_id: int
    rank: int
    front: str
    back: str


def process_quizlet_payloads(
    set_payload: str,
    *,
    api_payloads: list[str] | None = None,
    origin: str = "https://quizlet.com",
    path: str = "/",
    captured_at: str = "1970-01-01T00:00:00Z",
    session_id: str = "ses_quizlet",
    run_id: str = "run_quizlet",
    capabilities: frozenset[str] | set[str] = LIVE_CAPABILITIES,
    term_locale: str = "en",
    definition_locale: str = "en",
) -> PipelineResult:
    """Build a validated Razbiram deck from captured Quizlet JSON-bearing payloads."""
    state = _state_from_set_payload(set_payload)
    deck = _deck_from_state(state, term_locale=term_locale, definition_locale=definition_locale)
    initial = _items_from_state(state)
    paged = [item for payload in api_payloads or [] for item in _items_from_api_payload(payload)]
    items = _dedupe_items([*initial, *paged])

    target = Target(profile=TARGET_PROFILE, capabilities=sorted(capabilities))
    evidence: list[Evidence] = []
    cards: list[Card] = []
    for item in items:
        card, item_evidence = _card_from_item(
            item,
            origin=origin,
            path=path,
            captured_at=captured_at,
            run_id=run_id,
            term_locale=term_locale,
            definition_locale=definition_locale,
        )
        cards.append(card)
        evidence.extend(item_evidence)

    document = CaptureIR(
        sessionId=session_id,
        source=Source(
            kind="controlled-browser",
            policy="third-party-observe",
            origin=origin,
            path=path,
            capturedAt=captured_at,
        ),
        target=target,
        deck=deck,
        evidence=evidence,
        cards=cards,
    )
    issues = validate_for_export(document, capabilities=set(capabilities))
    result = export_deck(document, capabilities=set(capabilities))
    return PipelineResult(document=document, issues=issues, export=result, unsupported=[])


def process_quizlet_url(
    url: str,
    *,
    term_locale: str = "en",
    definition_locale: str = "en",
    capabilities: frozenset[str] | set[str] = LIVE_CAPABILITIES,
) -> PipelineResult:
    """Capture one user-supplied Quizlet set URL with Scrapling, then import its payloads.

    The network work is bounded to a single set page and its own pagination requests. If the page
    is blocked or Scrapling is unavailable, the caller receives a loud error instead of retries.
    """
    _validate_quizlet_url(url)
    fetcher = _scrapling_stealthy_fetcher()
    response = fetcher.fetch(
        url,
        headless=True,
        network_idle=False,
        disable_resources=True,
        timeout=90_000,
        wait=1000,
        capture_xhr=r".*studiable-item-documents.*",
        page_action=_fetch_remaining_pages,
    )
    page = response.body.decode(response.encoding or "utf-8", "replace")
    if response.status != 200 or not _NEXT_DATA.search(page):
        raise RuntimeError(f"Quizlet page was not captured cleanly: HTTP {response.status}")
    status = _capture_status(page)
    if any(entry.get("status", 200) >= 400 or entry.get("error") for entry in status):
        raise RuntimeError(f"Quizlet pagination failed: {status}")
    return process_quizlet_payloads(
        page,
        api_payloads=[
            xhr.body.decode(xhr.encoding or "utf-8", "replace") for xhr in response.captured_xhr
        ],
        origin=f"{urlparse(url).scheme}://{urlparse(url).netloc}",
        path=urlparse(url).path,
        term_locale=term_locale,
        definition_locale=definition_locale,
        capabilities=capabilities,
    )


def _validate_quizlet_url(url: str) -> None:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if parsed.scheme not in {"http", "https"} or not (
        host == "quizlet.com" or host.endswith(".quizlet.com")
    ):
        raise ValueError("only explicit quizlet.com URLs are accepted")


def _scrapling_stealthy_fetcher():
    try:
        return importlib.import_module("scrapling.fetchers").StealthyFetcher
    except ModuleNotFoundError:
        sibling = Path(__file__).resolve().parents[3].parent / "Scrapling"
        if sibling.is_dir():
            sys.path.insert(0, str(sibling))
            return importlib.import_module("scrapling.fetchers").StealthyFetcher
        raise RuntimeError(
            "Scrapling is not installed. Install it in this venv or keep a sibling Scrapling repo."
        ) from None


def _fetch_remaining_pages(page) -> None:
    page.evaluate(
        r"""
        async () => {
          const marker = document.createElement("script");
          marker.id = "__QUIZLET_CAPTURE_STATUS__";
          marker.type = "application/json";
          const statuses = [];
          try {
            const nextEl = document.querySelector("script#__NEXT_DATA__");
            if (!nextEl) throw new Error("Quizlet __NEXT_DATA__ was not found");
            const next = JSON.parse(nextEl.textContent);
            const state = JSON.parse(next.props.pageProps.dehydratedReduxStateKey);
            let paging = state.setPage.pagingMeta;
            const setId = state.setPage.set.id;
            const total = Number(paging.total || state.setPage.set.numTerms || 0);
            while (paging && paging.page * paging.perPage < total) {
              const params = new URLSearchParams();
              params.set("pagingToken", paging.token);
              params.set("page", String(paging.page + 1));
              params.set("perPage", String(paging.perPage));
              params.set("filters[studiableContainerId]", String(setId));
              params.set("filters[studiableContainerType]", "1");
              const response = await fetch(
                "/webapi/3.4/studiable-item-documents?" + params.toString(),
                { credentials: "include", headers: { accept: "application/json" } },
              );
              const text = await response.text();
              statuses.push({ status: response.status, url: response.url, bytes: text.length });
              if (!response.ok) break;
              const payload = JSON.parse(text);
              paging = payload.responses?.[0]?.paging || null;
              if (!paging) break;
            }
          } catch (error) {
            statuses.push({ error: String(error) });
          }
          marker.textContent = JSON.stringify(statuses);
          document.documentElement.appendChild(marker);
        }
        """
    )
    page.wait_for_timeout(3000)


def _capture_status(page: str) -> list[dict]:
    if _CAPTURE_MARKER not in page:
        return []
    text = page.split(_CAPTURE_MARKER, 1)[1].split("</script>", 1)[0]
    parsed = json.loads(text)
    return parsed if isinstance(parsed, list) else []


def _state_from_set_payload(payload: str) -> dict:
    data = _json_from_payload(payload)
    if "props" in data:
        page_props = data["props"].get("pageProps", {})
    elif "pageProps" in data:
        page_props = data["pageProps"]
    else:
        page_props = data
    state = page_props.get("dehydratedReduxStateKey")
    if isinstance(state, str):
        return json.loads(state)
    if isinstance(state, dict):
        return state
    raise ValueError("Quizlet set payload does not contain dehydratedReduxStateKey")


def _json_from_payload(payload: str) -> dict:
    stripped = payload.strip()
    match = _NEXT_DATA.search(stripped)
    if match:
        stripped = html.unescape(match.group(1))
    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise ValueError("Quizlet payload must be a JSON object")
    return parsed


def _deck_from_state(state: dict, *, term_locale: str, definition_locale: str) -> Deck:
    set_data = state.get("setPage", {}).get("set") or {}
    set_id = set_data.get("id") or "quizlet"
    title = clean_text(str(set_data.get("title") or "Quizlet deck"))
    description = clean_text(
        str(set_data.get("description") or "Imported from captured Quizlet data.")
    )
    deck_key = _slug(f"quizlet-{set_id}-{title}")
    return Deck(
        deckKey=deck_key,
        bookKey=None,
        title={term_locale: title},
        description={term_locale: description},
        level="general",
        difficulty="intermediate",
        languages={"source": term_locale, "target": definition_locale},
        tags=["quizlet", "captured"],
    )


def _slug(text: str) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "quizlet-deck"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return f"{stem[:48].rstrip('-')}-{digest}"


def _items_from_state(state: dict) -> list[QuizletItem]:
    raw = state.get("studyModesCommon", {}).get("studiableData", {}).get("studiableItems", [])
    return [_item_from_raw(item) for item in raw if isinstance(item, dict)]


def _items_from_api_payload(payload: str) -> list[QuizletItem]:
    data = _json_from_payload(payload)
    responses = data.get("responses")
    if not isinstance(responses, list) or not responses:
        raise ValueError("Quizlet API payload does not contain responses")
    models = responses[0].get("models", {})
    raw = models.get("studiableItem", [])
    return [_item_from_raw(item) for item in raw if isinstance(item, dict)]


def _item_from_raw(item: dict) -> QuizletItem:
    front = _side_text(item, "word")
    back = _side_text(item, "definition")
    if not front or not back:
        raise ValueError(f"Quizlet item {item.get('id')} is missing word or definition text")
    return QuizletItem(
        item_id=int(item["id"]),
        rank=int(item.get("rank", 0)),
        front=front,
        back=back,
    )


def _side_text(item: dict, label: str) -> str:
    for side in item.get("cardSides", []):
        if side.get("label") != label:
            continue
        media = side.get("media") or []
        return "\n".join(
            str(entry.get("plainText", "")).strip()
            for entry in media
            if str(entry.get("plainText", "")).strip()
        ).strip()
    return ""


def _dedupe_items(items: list[QuizletItem]) -> list[QuizletItem]:
    by_id: dict[int, QuizletItem] = {}
    for item in items:
        by_id[item.item_id] = item
    return sorted(by_id.values(), key=lambda item: (item.rank, item.item_id))


def _card_from_item(
    item: QuizletItem,
    *,
    origin: str,
    path: str,
    captured_at: str,
    run_id: str,
    term_locale: str,
    definition_locale: str,
) -> tuple[Card, list[Evidence]]:
    item_path = f"{path.rstrip('/')}/studiable-item/{item.item_id}"
    qfp = question_fingerprint(
        origin=origin,
        path=item_path,
        card_family="flashcard",
        question_text=item.front,
        option_texts=[],
    )
    capture = capture_id(
        created_at=captured_at,
        origin=origin,
        path=item_path,
        capture_state="quizlet-api-payload",
        question_fp=qfp,
        artifact_hashes=[],
    )
    source = source_id(origin=origin, path=item_path, question_fp=qfp)
    question_evidence = f"ev_quizlet_{item.item_id}_front"
    answer_evidence = f"ev_quizlet_{item.item_id}_back"
    front = Field_(value={term_locale: item.front}, evidence=[question_evidence], confidence=1.0)
    back = Field_(value={definition_locale: item.back}, evidence=[answer_evidence], confidence=1.0)
    card = Card(
        draftId=f"quizlet-{item.item_id}",
        cardId=card_id(source=source),
        sourceId=source,
        family="flashcard",
        prompt=front,
        front=front,
        back=back,
        answerEvidenceTier="source-verified",
        review=Review(status="approved", blockingReasons=[], reviewedBy=None, reviewedAt=None),
        rights=Rights(
            basis="personal-use-unconfirmed",
            licenseNotes=(
                "Imported from a user-provided Quizlet capture; publication rights are not "
                "confirmed."
            ),
            approvedForPublication=False,
        ),
    )
    return card, [
        Evidence(
            evidenceId=question_evidence,
            kind="dom",
            captureId=capture,
            sourceRole="question",
            authority="content",
            extractor="quizlet-payload.v1",
            runId=run_id,
        ),
        Evidence(
            evidenceId=answer_evidence,
            kind="dom",
            captureId=capture,
            sourceRole="answer-key",
            authority="content",
            extractor="quizlet-payload.v1",
            runId=run_id,
        ),
    ]
