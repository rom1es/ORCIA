"""Deterministic OpenAPI 3.1 exporter and domain-sharded TypeScript schema generator (`0-diff`).

Exports:
- `packages/api-client/openapi.json`
- `packages/api-client/src/generated/schema.ts`
- `packages/api-client/src/generated/<domain>.ts` (domain-sharded TypeScript types)

Supports `--check` mode to fail if committed artifacts drift from the live FastAPI schema.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[1]
for rel_src in (
    "packages/orcia-kernel/src",
    "packages/orcia-core/src",
    "packages/orcia-connectors/src",
    "apps/api/src",
    "apps/worker/src",
):
    candidate = str(REPO_ROOT / rel_src)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from orcia_api.main import create_app  # noqa: E402

SCHEMA_DOMAIN_MODULES: tuple[str, ...] = (
    "agents_and_skills",
    "auth_and_org",
    "blackboard",
    "bootstrap",
    "catalog",
    "ontology_and_rag",
    "orchestration",
    "permission_broker",
    "problem_details",
    "reflexive_execution",
    "shell",
)


def _json_schema_to_ts(schema: dict[str, Any], indent: int = 4) -> str:
    if "$ref" in schema:
        ref_name = str(schema["$ref"]).rsplit("/", 1)[-1]
        return f'components["schemas"]["{ref_name}"]'

    if "anyOf" in schema:
        parts = [_json_schema_to_ts(sub, indent) for sub in schema["anyOf"]]
        return " | ".join(dict.fromkeys(parts))

    if "enum" in schema:
        enum_vals = schema["enum"]
        return " | ".join(json.dumps(v) for v in enum_vals)

    if "const" in schema:
        return json.dumps(schema["const"])

    schema_type = schema.get("type")
    if schema_type == "string":
        return "string"
    if schema_type in ("integer", "number"):
        return "number"
    if schema_type == "boolean":
        return "boolean"
    if schema_type == "null":
        return "null"
    if schema_type == "array":
        item_ts = _json_schema_to_ts(schema.get("items", {}), indent)
        return f"({item_ts})[]"
    if schema_type == "object" or "properties" in schema:
        props: dict[str, Any] = schema.get("properties", {})
        required_set = set(schema.get("required", []))
        if not props:
            add_props = schema.get("additionalProperties")
            if isinstance(add_props, dict):
                val_ts = _json_schema_to_ts(add_props, indent)
                return f"Record<string, {val_ts}>"
            return "Record<string, unknown>"
        pad = " " * (indent + 2)
        closing_pad = " " * indent
        lines = ["{"]
        for prop_name, prop_schema in sorted(props.items()):
            opt = "" if prop_name in required_set else "?"
            prop_ts = _json_schema_to_ts(prop_schema, indent + 2)
            prop_key = prop_name if prop_name.isidentifier() else json.dumps(prop_name)
            lines.append(f"{pad}{prop_key}{opt}: {prop_ts};")
        lines.append(f"{closing_pad}}}")
        return "\n".join(lines)

    return "unknown"


def render_typescript_schema(openapi_spec: dict[str, Any]) -> str:
    """Render deterministic TypeScript definitions from an OpenAPI 3.1 specification."""
    schemas: dict[str, Any] = openapi_spec.get("components", {}).get("schemas", {})
    lines: list[str] = [
        "/**",
        " * AUTO-GENERATED FILE FROM FASTAPI OPENAPI 3.1 SCHEMA — DO NOT EDIT MANUALLY.",
        " * Regenerate via: `.venv/bin/python scripts/export_openapi.py`",
        " */",
        "",
        "export interface components {",
        "  schemas: {",
    ]

    for name in sorted(schemas.keys()):
        ts_body = _json_schema_to_ts(schemas[name], indent=4)
        schema_key = name if name.isidentifier() else json.dumps(name)
        lines.append(f"    {schema_key}: {ts_body};")

    lines.extend(
        [
            "  };",
            "}",
            "",
            "export interface paths {",
        ]
    )

    paths: dict[str, Any] = openapi_spec.get("paths", {})
    for path_key in sorted(paths.keys()):
        methods: dict[str, Any] = paths[path_key]
        lines.append(f'  "{path_key}": {{')
        for method in sorted(methods.keys()):
            op = methods[method]
            resp_200 = (
                op.get("responses", {})
                .get("200", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            resp_ts = _json_schema_to_ts(resp_200, indent=6) if resp_200 else "unknown"
            lines.append(f"    {method}: {{")
            lines.append("      responses: {")
            lines.append(f"        200: {resp_ts};")
            lines.append("      };")
            lines.append("    };")
        lines.append("  };")

    lines.append("}")
    lines.append("")
    for name in sorted(schemas.keys()):
        safe_alias = name if name.isidentifier() else name.replace("-", "_")
        lines.append(f'export type {safe_alias} = components["schemas"]["{name}"];')
    lines.append("")
    return "\n".join(lines)


def render_domain_shards(openapi_spec: dict[str, Any]) -> dict[str, str]:
    """Render domain-sharded TypeScript files mapped from `orcia_api.schemas.<domain>`."""
    schemas: dict[str, Any] = openapi_spec.get("components", {}).get("schemas", {})
    shards: dict[str, str] = {}

    for domain_mod in SCHEMA_DOMAIN_MODULES:
        mod = importlib.import_module(f"orcia_api.schemas.{domain_mod}")
        model_entries: list[tuple[str, str]] = []
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if not (issubclass(obj, BaseModel) and obj.__module__ == mod.__name__):
                continue
            disambiguated = f"orcia_api__schemas__{domain_mod}__{name}"
            if name in schemas:
                model_entries.append((name, name))
            elif disambiguated in schemas:
                model_entries.append((name, disambiguated))
        model_entries.sort(key=lambda item: item[0])
        header = (
            f" * AUTO-GENERATED DOMAIN SHARD (`{domain_mod}`) "
            f"FROM `orcia_api.schemas.{domain_mod}` — DO NOT EDIT MANUALLY."
        )
        lines: list[str] = [
            "/**",
            header,
            " * Regenerate via: `.venv/bin/python scripts/export_openapi.py`",
            " */",
            "",
            'import type { components } from "./schema";',
            "",
        ]
        for model_name, schema_ref_key in model_entries:
            lines.append(f'export type {model_name} = components["schemas"]["{schema_ref_key}"];')
        lines.append("")
        shards[f"{domain_mod}.ts"] = "\n".join(lines)

    return shards


def generate_openapi_artifacts() -> tuple[str, str, dict[str, str]]:
    """Return `(openapi_json_str, schema_ts_str, domain_shards)` deterministically."""
    app = create_app()
    spec = app.openapi()
    openapi_json = json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    schema_ts = render_typescript_schema(spec)
    domain_shards = render_domain_shards(spec)
    return openapi_json, schema_ts, domain_shards


def export_or_check(*, check_only: bool = False, output_root: Path | None = None) -> int:
    """Write or verify `openapi.json`, `src/generated/schema.ts`, and domain shards."""
    base_dir = output_root or (REPO_ROOT / "packages" / "api-client")
    openapi_path = base_dir / "openapi.json"
    generated_dir = base_dir / "src" / "generated"
    schema_ts_path = generated_dir / "schema.ts"

    expected_json, expected_ts, expected_shards = generate_openapi_artifacts()

    if check_only:
        if not openapi_path.exists() or not schema_ts_path.exists():
            return 1
        actual_json = openapi_path.read_text(encoding="utf-8")
        actual_ts = schema_ts_path.read_text(encoding="utf-8")
        if actual_json != expected_json or actual_ts != expected_ts:
            return 1
        for filename, expected_shard_content in expected_shards.items():
            shard_path = generated_dir / filename
            if not shard_path.exists():
                return 1
            if shard_path.read_text(encoding="utf-8") != expected_shard_content:
                return 1
        return 0

    openapi_path.parent.mkdir(parents=True, exist_ok=True)
    generated_dir.mkdir(parents=True, exist_ok=True)
    openapi_path.write_text(expected_json, encoding="utf-8")
    schema_ts_path.write_text(expected_ts, encoding="utf-8")
    for filename, shard_content in expected_shards.items():
        (generated_dir / filename).write_text(shard_content, encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for OpenAPI 3.1 export and 0-diff check."""
    parser = argparse.ArgumentParser(description="Export or check OpenAPI 3.1 SDK artifacts.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that committed OpenAPI artifacts have 0 diff against FastAPI.",
    )
    args = parser.parse_args(argv)
    return export_or_check(check_only=bool(args.check))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
