"""The committed JSON Schemas and their examples are the repo's public contracts.

These tests are the executable form of the contract-gate rules in
``docs/architecture/QUALITY_AND_CI.md``. They run offline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "docs" / "schemas"
SCHEMAS = sorted(SCHEMA_DIR.glob("*.schema.json"))


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_directory_is_not_empty() -> None:
    assert SCHEMAS, f"no *.schema.json found under {SCHEMA_DIR}"


@pytest.mark.parametrize("schema_path", SCHEMAS, ids=lambda p: p.name)
def test_schema_is_valid_draft_2020_12(schema_path: Path) -> None:
    Draft202012Validator.check_schema(_load(schema_path))


@pytest.mark.parametrize("schema_path", SCHEMAS, ids=lambda p: p.name)
def test_example_validates_against_its_schema(schema_path: Path) -> None:
    example_path = schema_path.with_name(schema_path.name.replace(".schema.json", ".example.json"))
    if not example_path.exists():
        pytest.skip(f"{schema_path.name} has no committed example")
    errors = sorted(
        Draft202012Validator(_load(schema_path)).iter_errors(_load(example_path)),
        key=lambda e: list(e.path),
    )
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)


def test_capture_ir_example_has_no_dangling_evidence_references() -> None:
    """Referential integrity is a code duty; JSON Schema cannot express it."""
    document = _load(SCHEMA_DIR / "capture-ir.v1.example.json")
    declared = {record["evidenceId"] for record in document.get("evidence", [])}
    referenced: set[str] = set()

    def collect(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "evidence" and isinstance(value, list):
                    referenced.update(item for item in value if isinstance(item, str))
                else:
                    collect(value)
        elif isinstance(node, list):
            for item in node:
                collect(item)

    collect(document.get("cards", []))
    assert referenced <= declared, f"dangling evidence ids: {sorted(referenced - declared)}"
