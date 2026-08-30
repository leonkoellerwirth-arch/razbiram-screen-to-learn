"""Generate the folder-level ``config.json`` that razbiram.com reads beside deck files."""

from __future__ import annotations

import re
from typing import Any


def _localized(value: object, fallback: str) -> dict[str, str]:
    if isinstance(value, dict):
        cleaned = {str(k): str(v) for k, v in value.items() if str(v).strip()}
        if cleaned:
            return cleaned
    if isinstance(value, str) and value.strip():
        return {"en": value.strip()}
    return {"en": fallback}


def _english(value: dict[str, str]) -> str:
    return value.get("en") or next(iter(value.values()), "")


def _topic_key(deck: dict[str, Any]) -> str:
    key = str(deck.get("bookKey") or deck.get("deckKey") or "captured-learncards")
    key = re.sub(r"-(?:deck-)?\d{1,3}$", "", key)
    return key or "captured-learncards"


def config_for_deck(deck: object, *, access_tier: str = "premium") -> dict:
    """Return a conservative razbiram learncards folder config for one validated deck."""
    if not isinstance(deck, dict):
        raise ValueError("deck must be a JSON object")
    deck_key = str(deck.get("deckKey") or "deck-01")
    meta = deck.get("meta") if isinstance(deck.get("meta"), dict) else {}
    title = _localized(meta.get("title"), deck_key)
    description = _localized(meta.get("description"), f"Practice deck: {_english(title)}")
    source_language = (
        meta.get("languages", {}).get("source") if isinstance(meta.get("languages"), dict) else None
    )
    config = {
        "topicKey": _topic_key(deck),
        "accessTier": access_tier,
        # Current live configs are mixed: some use access, newer examples use accessTier.
        # Writing both keeps the generated folder compatible with either loader shape.
        "access": access_tier,
        "level": str(meta.get("level") or "general"),
        "title": title,
        "description": description,
        "typedAnswerEvaluation": {
            "subject": _english(title),
            "domain": "general learning",
            "allowCrossLanguageEquivalence": False,
            "requireTerminologyPrecision": True,
            "evaluatorNotes": [
                "Require the answer to match the source card content.",
                "Reject answers that confuse neighbouring terms, definitions, or relations.",
            ],
        },
        "decks": {
            deck_key: {
                "description": description,
            }
        },
    }
    if isinstance(source_language, str) and source_language:
        config["typedAnswerEvaluation"]["targetAnswerLanguage"] = source_language
    return config
