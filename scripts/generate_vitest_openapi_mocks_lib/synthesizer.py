"""Deterministic schema example synthesizer for OpenAPI 3.1 JSON schemas (`T-D2`)."""

from __future__ import annotations

from typing import Any

FIXED_UUID_V7 = "0195f000-0000-7000-8000-000000000001"
FIXED_DATETIME_ISO = "2026-11-27T12:00:00Z"
FIXED_DATE_ISO = "2026-11-27"
MAX_SYNTH_DEPTH = 5


def _resolve_ref(
    schema: dict[str, Any],
    schemas: dict[str, dict[str, Any]],
    seen_refs: frozenset[str],
) -> tuple[dict[str, Any], frozenset[str], bool]:
    ref = schema.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/components/schemas/"):
        return schema, seen_refs, False
    ref_name = ref.rsplit("/", 1)[-1]
    if ref_name in seen_refs:
        return {}, seen_refs, True
    target = schemas.get(ref_name)
    if not isinstance(target, dict):
        return {}, seen_refs, True
    return target, seen_refs | {ref_name}, False


def _pick_union_branch(branches: list[Any]) -> dict[str, Any] | None:
    dict_branches = [b for b in branches if isinstance(b, dict)]
    if not dict_branches:
        return None
    for branch in dict_branches:
        if branch.get("type") != "null":
            return branch
    return dict_branches[0]


def _synth_string(schema: dict[str, Any], prop_name: str | None) -> str:
    fmt = schema.get("format")
    if fmt == "uuid":
        return FIXED_UUID_V7
    if fmt == "date-time":
        return FIXED_DATETIME_ISO
    if fmt == "date":
        return FIXED_DATE_ISO
    if fmt == "email":
        return "user@orcia.local"
    if fmt in ("uri", "url"):
        return "https://orcia.local/resource"
    min_len = int(schema.get("minLength") or 0)
    base = (prop_name or "orcia_mock").replace("-", "_")
    if len(base) < min_len:
        base = base + ("_x" * ((min_len - len(base) + 1) // 2))
        base = base[: max(min_len, len(base))]
    return base


def _synth_number(schema: dict[str, Any], *, is_int: bool) -> int | float:
    minimum = schema.get("minimum")
    excl_min = schema.get("exclusiveMinimum")
    val: float = 0.0
    if isinstance(minimum, (int, float)):
        val = max(val, float(minimum))
    if isinstance(excl_min, (int, float)):
        val = max(val, float(excl_min) + (1.0 if is_int else 0.1))
    return int(round(val)) if is_int else val


def synthesize_schema_example(
    raw_schema: dict[str, Any] | None,
    schemas: dict[str, dict[str, Any]],
    *,
    seen_refs: frozenset[str] = frozenset(),
    depth: int = 0,
    prop_name: str | None = None,
) -> Any:
    """Synthesize a deterministic JSON-serializable sample value from an OpenAPI schema."""
    if not isinstance(raw_schema, dict) or depth > MAX_SYNTH_DEPTH:
        return None

    schema, next_refs, is_cycle = _resolve_ref(raw_schema, schemas, seen_refs)
    if is_cycle:
        return {} if raw_schema.get("type") == "object" else None
    if "$ref" in schema and schema is not raw_schema:
        return synthesize_schema_example(
            schema, schemas, seen_refs=next_refs, depth=depth + 1, prop_name=prop_name
        )

    if "allOf" in schema and isinstance(schema["allOf"], list):
        merged_props: dict[str, Any] = {}
        merged_req: list[str] = []
        for sub in schema["allOf"]:
            if not isinstance(sub, dict):
                continue
            resolved_sub, sub_refs, sub_cycle = _resolve_ref(sub, schemas, next_refs)
            if sub_cycle:
                continue
            if isinstance(resolved_sub.get("properties"), dict):
                merged_props.update(resolved_sub["properties"])
            if isinstance(resolved_sub.get("required"), list):
                merged_req.extend(str(r) for r in resolved_sub["required"])
            next_refs = sub_refs
        if merged_props:
            return synthesize_schema_example(
                {"type": "object", "properties": merged_props, "required": merged_req},
                schemas,
                seen_refs=next_refs,
                depth=depth + 1,
                prop_name=prop_name,
            )
        if schema["allOf"] and isinstance(schema["allOf"][0], dict):
            return synthesize_schema_example(
                schema["allOf"][0],
                schemas,
                seen_refs=next_refs,
                depth=depth + 1,
                prop_name=prop_name,
            )

    for union_key in ("anyOf", "oneOf"):
        if union_key in schema and isinstance(schema[union_key], list):
            branch = _pick_union_branch(schema[union_key])
            if branch is None:
                return None
            return synthesize_schema_example(
                branch, schemas, seen_refs=next_refs, depth=depth + 1, prop_name=prop_name
            )

    if "const" in schema:
        return schema["const"]
    if "enum" in schema and isinstance(schema["enum"], list) and schema["enum"]:
        return schema["enum"][0]

    schema_type = schema.get("type")
    if "default" in schema and schema["default"] is not None:
        default_val = schema["default"]
        if not (
            schema_type == "string"
            and schema.get("format") == "uuid"
            and not isinstance(default_val, str)
        ):
            return default_val

    if schema_type == "null":
        return None
    if schema_type == "boolean":
        return False
    if schema_type == "integer":
        return _synth_number(schema, is_int=True)
    if schema_type == "number":
        return _synth_number(schema, is_int=False)
    if schema_type == "string":
        return _synth_string(schema, prop_name)
    if schema_type == "array":
        min_items = int(schema.get("minItems") or 0)
        if min_items <= 0:
            return []
        item_schema = schema.get("items") if isinstance(schema.get("items"), dict) else {}
        item_val = synthesize_schema_example(
            item_schema, schemas, seen_refs=next_refs, depth=depth + 1, prop_name=prop_name
        )
        return [item_val for _ in range(min_items)]

    props = schema.get("properties")
    if schema_type == "object" or isinstance(props, dict):
        out: dict[str, Any] = {}
        if isinstance(props, dict):
            for key in sorted(props):
                prop_schema = props[key]
                if not isinstance(prop_schema, dict):
                    continue
                out[key] = synthesize_schema_example(
                    prop_schema, schemas, seen_refs=next_refs, depth=depth + 1, prop_name=key
                )
        return out

    return {}


def extract_operation_mock_spec(
    operation: dict[str, Any],
    schemas: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Return `{\"status\": int, \"body\": Any}` for an OpenAPI operation."""
    responses = operation.get("responses")
    if not isinstance(responses, dict) or not responses:
        return {"status": 200, "body": {}}

    success_codes = sorted(
        code for code in responses if str(code).isdigit() and 200 <= int(str(code)) < 300
    )
    chosen_code = success_codes[0] if success_codes else sorted(responses.keys())[0]
    status_int = int(chosen_code) if str(chosen_code).isdigit() else 200
    resp_obj = responses.get(chosen_code, {})
    if status_int == 204 or not isinstance(resp_obj, dict):
        return {"status": 204 if status_int == 204 else status_int, "body": None}

    content = resp_obj.get("content")
    if not isinstance(content, dict):
        return {"status": status_int, "body": None}

    json_media = content.get("application/json")
    if not isinstance(json_media, dict):
        return {"status": status_int, "body": None}

    schema = json_media.get("schema")
    if not isinstance(schema, dict):
        return {"status": status_int, "body": {}}
    body = synthesize_schema_example(schema, schemas)
    return {"status": status_int, "body": body}
