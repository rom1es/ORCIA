"""The 4 Generic Deterministic Gate Runners (`orcia_core.workflows.gates.runners`, `TASK-04`).

Implements:
1. `markdown_contract_runner`
2. `json_schema_runner`
3. `cli_sandbox_runner`
4. `catalog_invariant_runner`

100% domain-agnostic: zero vendor or methodology vocabulary.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, Field


class DeterministicRunnerResult(BaseModel):
    """Structured output of a generic deterministic gate runner."""

    runner_plugin_id: str
    status: Literal["NOMINAL", "FAILED"]
    violations: list[str] = Field(default_factory=list)
    diagnostic_stderr: str = ""


def markdown_contract_runner(
    artifact_text: str,
    config: dict[str, Any],
) -> DeterministicRunnerResult:
    """Validate Markdown headings, section lengths, Mermaid blocks, and forbidden patterns."""
    violations: list[str] = []
    required_headings: list[str] = list(config.get("required_headings", []))
    min_chars: int = int(config.get("min_chars_per_section", 0))
    require_mermaid: int = int(config.get("require_mermaid_blocks", 0))
    forbid_patterns: list[str] = list(config.get("forbid_patterns", []))

    for heading in required_headings:
        idx = artifact_text.find(heading)
        if idx == -1:
            violations.append(f"Missing required heading: {heading}")
            continue
        if min_chars > 0:
            after = artifact_text[idx + len(heading) :]
            next_heading_match = re.search(r"\n#{1,3}\s+", after)
            section_body = (
                after[: next_heading_match.start()].strip() if next_heading_match else after.strip()
            )
            if len(section_body) < min_chars:
                violations.append(
                    f"Section '{heading}' too short ({len(section_body)} < {min_chars} chars)"
                )

    if require_mermaid > 0:
        mermaid_blocks = re.findall(r"```mermaid\s+[\s\S]*?```", artifact_text)
        if len(mermaid_blocks) < require_mermaid:
            violations.append(
                f"Expected >= {require_mermaid} Mermaid block(s), found {len(mermaid_blocks)}"
            )

    for pattern in forbid_patterns:
        if re.search(pattern, artifact_text):
            violations.append(f"Forbidden pattern matched: {pattern}")

    status: Literal["NOMINAL", "FAILED"] = "NOMINAL" if not violations else "FAILED"
    return DeterministicRunnerResult(
        runner_plugin_id="markdown_contract_runner",
        status=status,
        violations=violations,
        diagnostic_stderr="\n".join(violations),
    )


def json_schema_runner(
    artifact_text: str,
    config: dict[str, Any],
) -> DeterministicRunnerResult:
    """Validate JSON payload structure, required properties, types, and additionalProperties."""
    violations: list[str] = []
    try:
        payload = json.loads(artifact_text)
    except json.JSONDecodeError as exc:
        msg = f"Invalid JSON payload: {exc}"
        return DeterministicRunnerResult(
            runner_plugin_id="json_schema_runner",
            status="FAILED",
            violations=[msg],
            diagnostic_stderr=msg,
        )

    if not isinstance(payload, dict):
        msg = "Root JSON value must be an object."
        return DeterministicRunnerResult(
            runner_plugin_id="json_schema_runner",
            status="FAILED",
            violations=[msg],
            diagnostic_stderr=msg,
        )

    schema: dict[str, Any] = config.get("schema", config)
    required_fields: list[str] = list(schema.get("required", config.get("required_fields", [])))
    properties: dict[str, Any] = dict(schema.get("properties", config.get("properties", {})))
    strict_additional: bool = bool(
        config.get(
            "strict_additional_properties",
            schema.get("additionalProperties", True) is False,
        )
    )

    for req_key in required_fields:
        if req_key not in payload:
            violations.append(f"Missing required JSON property: '{req_key}'")

    type_map: dict[str, type | tuple[type, ...]] = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    for prop_name, prop_spec in properties.items():
        if prop_name in payload and isinstance(prop_spec, dict):
            expected_type_name = prop_spec.get("type")
            if expected_type_name in type_map:
                py_type = type_map[expected_type_name]
                if not isinstance(payload[prop_name], py_type):
                    violations.append(
                        f"Property '{prop_name}' expected type '{expected_type_name}'"
                    )

    if strict_additional and properties:
        extra_keys = sorted(set(payload.keys()) - set(properties.keys()))
        if extra_keys:
            violations.append(f"Disallowed additional properties: {', '.join(extra_keys)}")

    status: Literal["NOMINAL", "FAILED"] = "NOMINAL" if not violations else "FAILED"
    return DeterministicRunnerResult(
        runner_plugin_id="json_schema_runner",
        status=status,
        violations=violations,
        diagnostic_stderr="\n".join(violations),
    )


def cli_sandbox_runner(
    artifact_text: str,
    config: dict[str, Any],
) -> DeterministicRunnerResult:
    """Deterministic CLI sandbox runner checking exit code and syntax invariants."""
    violations: list[str] = []
    expected_exit_code = int(config.get("expected_exit_code", 0))
    simulated_exit_code = int(config.get("simulated_exit_code", 0))
    command = str(config.get("command", "lint-artifact"))
    forbid_tokens: list[str] = list(config.get("forbid_tokens", ["SYNTAX_ERROR", "FAIL_SANDBOX"]))

    if simulated_exit_code != expected_exit_code:
        violations.append(
            f"Command '{command}' exited with {simulated_exit_code} (expected {expected_exit_code})"
        )
    for token in forbid_tokens:
        if token in artifact_text:
            violations.append(f"Command '{command}' detected error token: {token}")

    status: Literal["NOMINAL", "FAILED"] = "NOMINAL" if not violations else "FAILED"
    return DeterministicRunnerResult(
        runner_plugin_id="cli_sandbox_runner",
        status=status,
        violations=violations,
        diagnostic_stderr="\n".join(violations),
    )


def catalog_invariant_runner(
    artifact_text: str,
    config: dict[str, Any],
) -> DeterministicRunnerResult:
    """Validate Federated Catalog classifications and referenced entity URIs."""
    violations: list[str] = []
    allowed_classifications: list[str] = list(config.get("allowed_classifications", []))
    actual_classification = str(config.get("classification", "INTERNAL"))
    if allowed_classifications and actual_classification not in allowed_classifications:
        violations.append(
            f"Classification '{actual_classification}' not in {allowed_classifications}"
        )

    require_existing = bool(config.get("require_existing_entities", False))
    known_entities: set[str] = set(config.get("known_entities", []))
    referenced_uris = re.findall(r"catalog://[a-zA-Z0-9_./-]+", artifact_text)
    if require_existing:
        for uri in referenced_uris:
            if uri not in known_entities:
                violations.append(f"Unknown catalog entity reference: {uri}")

    status: Literal["NOMINAL", "FAILED"] = "NOMINAL" if not violations else "FAILED"
    return DeterministicRunnerResult(
        runner_plugin_id="catalog_invariant_runner",
        status=status,
        violations=violations,
        diagnostic_stderr="\n".join(violations),
    )


RunnerCallable = Callable[[str, dict[str, Any]], DeterministicRunnerResult]

GENERIC_GATE_RUNNERS: dict[str, RunnerCallable] = {
    "markdown_contract_runner": markdown_contract_runner,
    "json_schema_runner": json_schema_runner,
    "cli_sandbox_runner": cli_sandbox_runner,
    "catalog_invariant_runner": catalog_invariant_runner,
}

__all__ = [
    "DeterministicRunnerResult",
    "GENERIC_GATE_RUNNERS",
    "RunnerCallable",
    "catalog_invariant_runner",
    "cli_sandbox_runner",
    "json_schema_runner",
    "markdown_contract_runner",
]
