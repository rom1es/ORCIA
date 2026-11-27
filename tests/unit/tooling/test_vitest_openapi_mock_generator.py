"""Unit tests for deterministic OpenAPI Vitest mock generator (`T-D2`, Story 32.5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.generate_vitest_openapi_mocks import (
    build_operation_specs,
    generate_or_check,
    render_typescript_mocks,
)
from scripts.generate_vitest_openapi_mocks_lib.synthesizer import (
    FIXED_DATETIME_ISO,
    FIXED_UUID_V7,
    synthesize_schema_example,
)

pytestmark = pytest.mark.story("32.5")
REPO_ROOT = Path(__file__).resolve().parents[3]


def test_synthesizer_handles_refs_cycles_unions_allof_enums_and_formats() -> None:
    schemas = {
        "Node": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "created_at": {"type": "string", "format": "date-time"},
                "mode": {"type": "string", "enum": ["FAST", "DEEP"]},
                "parent": {"anyOf": [{"$ref": "#/components/schemas/Node"}, {"type": "null"}]},
            },
        },
        "Extended": {
            "allOf": [
                {"$ref": "#/components/schemas/Node"},
                {
                    "type": "object",
                    "properties": {"count": {"type": "integer", "minimum": 2}},
                },
            ]
        },
    }
    sample = synthesize_schema_example({"$ref": "#/components/schemas/Extended"}, schemas)
    assert sample["id"] == FIXED_UUID_V7
    assert sample["created_at"] == FIXED_DATETIME_ISO
    assert sample["mode"] == "FAST"
    assert sample["count"] == 2
    assert sample["parent"] is None


def test_build_operation_specs_handles_204_and_check_mode_detects_drift(tmp_path: Path) -> None:
    openapi_doc = {
        "openapi": "3.1.0",
        "paths": {
            "/api/v1/items/{item_id}": {
                "delete": {"responses": {"204": {"description": "No Content"}}},
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Item"}
                                }
                            }
                        }
                    }
                },
            }
        },
        "components": {
            "schemas": {
                "Item": {
                    "type": "object",
                    "properties": {
                        "item_id": {"type": "string", "format": "uuid"},
                        "status": {"type": "string", "enum": ["ACTIVE", "DRAFT"]},
                    },
                }
            }
        },
    }
    specs = build_operation_specs(openapi_doc)
    assert specs["DELETE /api/v1/items/{item_id}"] == {"status": 204, "body": None}
    assert specs["GET /api/v1/items/{item_id}"] == {
        "status": 200,
        "body": {"item_id": FIXED_UUID_V7, "status": "ACTIVE"},
    }

    oa_path = tmp_path / "openapi.json"
    out_path = tmp_path / "generatedOpenApiMocks.ts"
    oa_path.write_text(json.dumps(openapi_doc), encoding="utf-8")

    assert generate_or_check(oa_path, out_path, check=True) == 1
    assert generate_or_check(oa_path, out_path, check=False) == 0
    assert generate_or_check(oa_path, out_path, check=True) == 0

    ts_src = render_typescript_mocks(specs)
    assert "buildOpenApiMockPayload" in ts_src
    assert "buildOpenApiMockResponse" in ts_src
    out_path.write_text(ts_src + "\n// drift\n", encoding="utf-8")
    assert generate_or_check(oa_path, out_path, check=True) == 1


def test_live_generated_vitest_openapi_mocks_zero_diff() -> None:
    rc = generate_or_check(
        REPO_ROOT / "packages" / "api-client" / "openapi.json",
        REPO_ROOT / "apps" / "web" / "src" / "__tests__" / "setup" / "generatedOpenApiMocks.ts",
        check=True,
    )
    assert rc == 0
