from __future__ import annotations

from razbiram_screen_to_learn.config_export import config_for_deck


def test_config_references_the_deck_file_key_and_folder_topic() -> None:
    deck = {
        "schemaId": "studywithme-bg.learncard.v1",
        "bookKey": "iso-iec-27001-2022-lead-auditor-01",
        "deckKey": "iso-iec-27001-2022-lead-auditor-01",
        "meta": {
            "title": {"en": "ISO/IEC 27001:2022 Lead Auditor"},
            "description": {"en": "Quizlet import practice cards."},
            "languages": {"source": "en"},
        },
        "cards": [],
    }

    config = config_for_deck(deck)

    assert config["topicKey"] == "iso-iec-27001-2022-lead-auditor"
    assert config["accessTier"] == "premium"
    assert config["access"] == "premium"
    assert config["title"] == {"en": "ISO/IEC 27001:2022 Lead Auditor"}
    assert config["description"] == {"en": "Quizlet import practice cards."}
    assert config["decks"] == {
        "iso-iec-27001-2022-lead-auditor-01": {
            "description": {"en": "Quizlet import practice cards."}
        }
    }
    assert config["typedAnswerEvaluation"]["targetAnswerLanguage"] == "en"


def test_config_has_safe_defaults_for_minimal_decks() -> None:
    config = config_for_deck({"deckKey": "deck-01"})

    assert config["topicKey"] == "deck"
    assert config["title"] == {"en": "deck-01"}
    assert config["decks"]["deck-01"]["description"] == {"en": "Practice deck: deck-01"}
