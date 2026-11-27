"""The generated OpenAPI schema stays compatible with the design contract.

Constitution IX, FR-003: contracts/openapi-health.yaml is the agreed shape of
``GET /api/health``; this test fails when the models drift from it.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi import FastAPI

from app.api.health import HealthReport

CONTRACT = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "001-walking-skeleton"
    / "contracts"
    / "openapi-health.yaml"
)
SCHEMAS = ("HealthReport", "DatabaseStatus", "LLMStatus")

Schema = dict[str, Any]


@pytest.fixture(scope="module")
def contract() -> Schema:
    with CONTRACT.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def generated(app_factory: Callable[..., FastAPI]) -> Schema:
    return app_factory().openapi()


def _ref_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def _shape(prop: Schema) -> dict[str, Any]:
    """What a property means, without titles: types, enum, format or ref target.

    ``type: [string, "null"]`` and ``anyOf: [{type: string}, {type: null}]`` both
    become ``{"types": {"string", "null"}}``.
    """
    if "$ref" in prop:
        return {"ref": _ref_name(prop["$ref"])}
    variants = prop.get("anyOf", [prop])
    types: set[str] = set()
    shape: dict[str, Any] = {}
    for variant in variants:
        declared = variant.get("type")
        types.update(declared if isinstance(declared, list) else [declared])
        if "enum" in variant:
            shape["enum"] = sorted(variant["enum"])
        elif "const" in variant:
            # Pydantic renders a one-value Literal as const; JSON Schema treats
            # ``const: x`` and ``enum: [x]`` as the same constraint.
            shape["enum"] = [variant["const"]]
        if "format" in variant:
            shape["format"] = variant["format"]
    shape["types"] = types
    return shape


def test_operation_id(contract: Schema, generated: Schema) -> None:
    assert contract["paths"]["/api/health"]["get"]["operationId"] == "getHealth"
    assert generated["paths"]["/api/health"]["get"]["operationId"] == "getHealth"


def test_response_schema_is_health_report(generated: Schema) -> None:
    response = generated["paths"]["/api/health"]["get"]["responses"]["200"]
    schema = response["content"]["application/json"]["schema"]
    assert _ref_name(schema["$ref"]) == "HealthReport"


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_matches_contract(
    contract: Schema, generated: Schema, name: str
) -> None:
    expected = contract["components"]["schemas"][name]
    actual = generated["components"]["schemas"][name]

    assert set(actual["properties"]) == set(expected["properties"])
    assert sorted(actual.get("required", [])) == sorted(expected["required"])
    for prop, spec in expected["properties"].items():
        assert _shape(actual["properties"][prop]) == _shape(spec), prop


def test_contract_examples_validate(contract: Schema) -> None:
    response = contract["paths"]["/api/health"]["get"]["responses"]["200"]
    examples = response["content"]["application/json"]["examples"]
    assert examples
    for name, example in examples.items():
        report = HealthReport.model_validate(example["value"])
        assert report.status == "ok", name
