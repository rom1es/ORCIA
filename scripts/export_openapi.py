"""Deterministic OpenAPI 3.1 exporter and TypeScript schema generator (`0-diff` gate, AD-1).

Exports:
- `packages/api-client/openapi.json`
- `packages/api-client/src/generated/schema.ts`

Supports `--check` mode to fail if committed artifacts drift from the live FastAPI schema.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
for rel_src in ("packages/orcia-core/src", "apps/api/src", "apps/worker/src"):
    candidate = str(REPO_ROOT / rel_src)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from orcia_api.main import create_app  # noqa: E402


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
            return "Record<string, unknown>"
        pad = " " * (indent + 2)
        closing_pad = " " * indent
        lines = ["{"]
        for prop_name, prop_schema in sorted(props.items()):
            opt = "" if prop_name in required_set else "?"
            prop_ts = _json_schema_to_ts(prop_schema, indent + 2)
            lines.append(f"{pad}{prop_name}{opt}: {prop_ts};")
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
        lines.append(f"    {name}: {ts_body};")

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

    lines.extend(
        [
            "}",
            "",
            'export type ProblemDetails = components["schemas"]["ProblemDetails"];',
            'export type HealthResponse = components["schemas"]["HealthResponse"];',
            'export type ShellModuleItem = components["schemas"]["ShellModuleItem"];',
            'export type ScopeNode = components["schemas"]["ScopeNode"];',
            'export type HumanProfileBadge = components["schemas"]["HumanProfileBadge"];',
            (
                "export type ShellNavigationResponse = "
                'components["schemas"]["ShellNavigationResponse"];'
            ),
            "",
        ]
    )
    return "\n".join(lines)


def generate_openapi_artifacts() -> tuple[str, str]:
    """Return `(openapi_json_str, schema_ts_str)` deterministically."""
    app = create_app()
    spec = app.openapi()
    openapi_json = json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    schema_ts = render_typescript_schema(spec)
    return openapi_json, schema_ts


def export_or_check(*, check_only: bool = False, output_root: Path | None = None) -> int:
    """Write or verify `openapi.json` and `src/generated/schema.ts`."""
    base_dir = output_root or (REPO_ROOT / "packages" / "api-client")
    openapi_path = base_dir / "openapi.json"
    schema_ts_path = base_dir / "src" / "generated" / "schema.ts"

    expected_json, expected_ts = generate_openapi_artifacts()

    if check_only:
        if not openapi_path.exists() or not schema_ts_path.exists():
            return 1
        actual_json = openapi_path.read_text(encoding="utf-8")
        actual_ts = schema_ts_path.read_text(encoding="utf-8")
        if actual_json != expected_json or actual_ts != expected_ts:
            return 1
        return 0

    openapi_path.parent.mkdir(parents=True, exist_ok=True)
    schema_ts_path.parent.mkdir(parents=True, exist_ok=True)
    openapi_path.write_text(expected_json, encoding="utf-8")
    schema_ts_path.write_text(expected_ts, encoding="utf-8")
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
