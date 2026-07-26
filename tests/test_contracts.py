"""Agreement between the committed JSON Schema and the typed Python view, plus the cross-field
rules that JSON Schema cannot express.

The committed example is the shared fixture: if the schema and the models ever disagree about it,
one of them has drifted.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from razbiram_screen_to_learn.contracts import CaptureIR
from razbiram_screen_to_learn.validators import validate_document, validate_for_export

EXAMPLE = Path(__file__).resolve().parents[1] / "docs" / "schemas" / "capture-ir.v1.example.json"


@pytest.fixture
def raw() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def document(raw: dict) -> CaptureIR:
    return CaptureIR.model_validate(raw)


class TestSchemaModelAgreement:
    def test_committed_example_parses(self, document: CaptureIR) -> None:
        assert document.schemaVersion == "capture-ir.v1"
        assert document.cards

    def test_round_trip_preserves_every_field(self, raw: dict, document: CaptureIR) -> None:
        emitted = document.model_dump(mode="json", exclude_none=True)
        assert emitted == raw

    def test_unknown_fields_are_rejected(self, raw: dict) -> None:
        """extra="forbid" mirrors unevaluatedProperties: false — a typo must be loud."""
        broken = copy.deepcopy(raw)
        broken["cards"][0]["corectOptionIds"] = ["opt_a"]
        with pytest.raises(ValueError, match="corectOptionIds"):
            CaptureIR.model_validate(broken)


class TestCrossFieldValidation:
    def test_committed_example_is_internally_consistent(self, document: CaptureIR) -> None:
        assert validate_document(document) == []

    def test_option_set_mismatch_is_reported(self, raw: dict) -> None:
        broken = copy.deepcopy(raw)
        broken["cards"][0]["correctOptionIds"] = []
        issues = validate_document(CaptureIR.model_validate(broken))
        assert any(issue.code == "option-set-mismatch" for issue in issues)

    def test_dangling_evidence_is_reported(self, raw: dict) -> None:
        """The defect the committed example itself shipped with until 2026-07-26."""
        broken = copy.deepcopy(raw)
        broken["evidence"] = []
        issues = validate_document(CaptureIR.model_validate(broken))
        assert any(issue.code == "dangling-evidence" for issue in issues)

    def test_unresolved_review_blocks(self, raw: dict) -> None:
        broken = copy.deepcopy(raw)
        broken["cards"][0]["review"]["blockingReasons"] = ["answer not visible in source"]
        issues = validate_document(CaptureIR.model_validate(broken))
        assert any(issue.code == "unresolved-review" for issue in issues)

    def test_duplicate_card_ids_are_reported(self, raw: dict) -> None:
        broken = copy.deepcopy(raw)
        broken["cards"].append(copy.deepcopy(broken["cards"][0]))
        issues = validate_document(CaptureIR.model_validate(broken))
        assert any(issue.code == "duplicate-card-id" for issue in issues)


class TestExportGate:
    def test_multiple_select_is_blocked_without_the_capability(self, document: CaptureIR) -> None:
        """BIBLE invariant 5. The live razbiram.com MCQ runtime is single-answer only."""
        assert document.cards[0].family == "multiple-select"
        issues = validate_for_export(document, capabilities={"mcq.single"})
        assert any(issue.code == "capability-missing" for issue in issues)

    def test_multiple_select_passes_with_the_capability(self, document: CaptureIR) -> None:
        issues = validate_for_export(
            document, capabilities={"mcq.single", "mcq.multiple-select.v1"}
        )
        assert not any(issue.code == "capability-missing" for issue in issues)

    def test_unqualified_evidence_blocks_export(self, raw: dict) -> None:
        broken = copy.deepcopy(raw)
        broken["cards"][0]["answerEvidenceTier"] = "model-inferred"
        issues = validate_for_export(
            CaptureIR.model_validate(broken), capabilities={"mcq.multiple-select.v1"}
        )
        assert any(issue.code == "unqualified-evidence" for issue in issues)

    def test_missing_evidence_tier_blocks_export(self, raw: dict) -> None:
        broken = copy.deepcopy(raw)
        broken["cards"][0].pop("answerEvidenceTier", None)
        issues = validate_for_export(
            CaptureIR.model_validate(broken), capabilities={"mcq.multiple-select.v1"}
        )
        assert any(issue.code == "missing-evidence-tier" for issue in issues)
