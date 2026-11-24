"""YAML/JSON line-tracking loader and step specification parser for Workflow-as-Code (Story 3.1).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`) and zero SDLC
vocabulary (`AD-19`, `AD-20`, `AC-E2`).
"""

from __future__ import annotations

from typing import Any

import yaml  # type: ignore[import-untyped]

from orcia_core.orchestration._orchestration_yaml_locales import get_yaml_copy
from orcia_core.orchestration._yaml_policy_plugins import (
    WorkflowPolicyPluginProtocol,
    get_valid_workflow_modes,
    get_workflow_policy_plugins,
    is_registered_workflow_policy,
    register_workflow_policy_plugin,
)
from orcia_core.orchestration.models import (
    WorkflowStepSpec,
    WorkflowValidationFinding,
)

VALID_CRITICALITIES = frozenset({"LOW_NON_CRITICAL", "STANDARD", "HIGH_CRITICAL"})
VALID_EXECUTION_REGIMES = frozenset(
    {"INTERACTIVE_COACHING", "BACKGROUND_FAST_PATH", "AUTONOMOUS_CONTRACT"}
)
VALID_TIE_BREAK_POLICIES = frozenset(
    {"ONTOLOGY_AXIOM_FIRST", "DEFER_AND_CONTINUE_WITH_ASSUMPTION", "PAUSE_AND_ESCALATE"}
)
VALID_STEP_TYPES = frozenset(
    {"AGENT", "SKILL", "SUB_WORKFLOW", "HUMAN_TASK", "HTTP_ACTION", "POST_ACTION_VERIFICATION"}
)
VALID_GATE_POLICIES = frozenset({"STRICT", "STANDARD", "FAST_TRACK"})
VALID_MODES: frozenset[str] = frozenset({"standard"})


class _LineTrackingLoader(yaml.SafeLoader):  # type: ignore[misc]
    """Custom YAML SafeLoader recording 1-indexed line numbers on mappings."""


def _construct_mapping_with_lines(
    loader: _LineTrackingLoader, node: Any, deep: bool = False
) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    line_map: dict[str, int] = {}
    for key_node, value_node in node.value:
        key = str(loader.construct_object(key_node, deep=deep))
        mapping[key] = loader.construct_object(value_node, deep=deep)
        line_map[key] = int(key_node.start_mark.line) + 1
    mapping["__lines__"] = line_map
    mapping["__node_line__"] = int(node.start_mark.line) + 1
    return mapping


_LineTrackingLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping_with_lines
)


def line_of(mapping: dict[str, Any], key: str, default: int = 1) -> int:
    """Resolve 1-indexed line number for a key inside a YAML/JSON mapping."""
    lines = mapping.get("__lines__")
    if isinstance(lines, dict) and isinstance(lines.get(key), int):
        return int(lines[key])
    node_line = mapping.get("__node_line__")
    return int(node_line) if isinstance(node_line, int) else default


def clean_str_dict(raw: Any) -> dict[str, str]:
    """Strip internal line metadata from a parsed string-to-string dictionary."""
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items() if k not in ("__lines__", "__node_line__")}


def parse_raw_yaml_or_json(
    raw_text: str,
) -> tuple[dict[str, Any], list[WorkflowValidationFinding]]:
    """Parse YAML or JSON text and return root dict with line numbers or syntax findings."""
    yc = get_yaml_copy()
    if not raw_text or not raw_text.strip():
        return {}, [
            WorkflowValidationFinding(
                line=1,
                rule_code="RULE_SYNTAX_EMPTY_MANIFEST",
                field_path="root",
                message=yc["empty_manifest"],
            )
        ]
    try:
        loaded = yaml.load(raw_text, Loader=_LineTrackingLoader)  # noqa: S506
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        err_line = (int(mark.line) + 1) if mark is not None else 1
        return {}, [
            WorkflowValidationFinding(
                line=err_line,
                rule_code="RULE_YAML_JSON_SYNTAX_ERROR",
                field_path="root",
                message=yc["syntax_error"].format(line=err_line, exc=exc),
            )
        ]

    if not isinstance(loaded, dict):
        return {}, [
            WorkflowValidationFinding(
                line=1,
                rule_code="RULE_ROOT_MAPPING_REQUIRED",
                field_path="root",
                message=yc["root_mapping"],
            )
        ]
    return loaded, []


def parse_single_step_spec(
    raw_step: Any,
    idx: int,
    steps_line: int,
    seen_keys: set[str],
    findings: list[WorkflowValidationFinding],
) -> WorkflowStepSpec | None:
    """Validate and convert a raw YAML step dict into a `WorkflowStepSpec`."""
    yc = get_yaml_copy()
    if not isinstance(raw_step, dict):
        findings.append(
            WorkflowValidationFinding(
                line=steps_line,
                rule_code="RULE_STEP_OBJECT_REQUIRED",
                field_path=f"steps[{idx}]",
                message=yc["step_object"],
            )
        )
        return None

    s_line = line_of(raw_step, "step_key", int(raw_step.get("__node_line__", steps_line)))
    step_key = str(raw_step.get("step_key", "")).strip()
    if not step_key:
        findings.append(
            WorkflowValidationFinding(
                line=s_line,
                rule_code="RULE_STEP_KEY_REQUIRED",
                field_path=f"steps[{idx}].step_key",
                message=yc["step_key_required"],
            )
        )
        return None
    if step_key in seen_keys:
        findings.append(
            WorkflowValidationFinding(
                line=s_line,
                rule_code="RULE_STEP_KEY_UNIQUE",
                field_path=f"steps[{idx}].step_key",
                message=yc["step_key_unique"].format(step_key=step_key, line=s_line),
            )
        )
        return None
    seen_keys.add(step_key)

    raw_type = str(raw_step.get("step_type", "AGENT")).strip()
    if raw_type not in VALID_STEP_TYPES:
        findings.append(
            WorkflowValidationFinding(
                line=line_of(raw_step, "step_type", s_line),
                rule_code="RULE_INVALID_STEP_TYPE",
                field_path=f"steps[{idx}].step_type",
                message=yc["invalid_step_type"].format(step_type=raw_type),
            )
        )
        return None

    sub_wf_uri = raw_step.get("sub_workflow_uri")
    if raw_type == "SUB_WORKFLOW" and (not isinstance(sub_wf_uri, str) or not sub_wf_uri.strip()):
        findings.append(
            WorkflowValidationFinding(
                line=line_of(raw_step, "sub_workflow_uri", s_line),
                rule_code="RULE_SUB_WORKFLOW_URI_REQUIRED",
                field_path=f"steps[{idx}].sub_workflow_uri",
                message=yc["subwf_uri_required"].format(step_key=step_key),
            )
        )

    max_retries = raw_step.get("max_agent_retries", 3)
    if (
        not isinstance(max_retries, int)
        or isinstance(max_retries, bool)
        or not (1 <= max_retries <= 10)
    ):
        findings.append(
            WorkflowValidationFinding(
                line=line_of(raw_step, "max_agent_retries", s_line),
                rule_code="RULE_BOUNDED_AGENT_RETRIES",
                field_path=f"steps[{idx}].max_agent_retries",
                message=yc["bounded_retries"],
            )
        )
        max_retries = 3

    raw_deps = raw_step.get("depends_on", [])
    depends_on = (
        tuple(str(d).strip() for d in raw_deps if str(d).strip())
        if isinstance(raw_deps, list)
        else ()
    )
    raw_kb = raw_step.get("kb_uris", [])
    kb_uris = tuple(str(u) for u in raw_kb if str(u).strip()) if isinstance(raw_kb, list) else ()
    ver_win = raw_step.get("verification_window_seconds")

    raw_tags = raw_step.get("tags", [])
    tag_list: list[str] = (
        [str(t).strip() for t in raw_tags if str(t).strip()] if isinstance(raw_tags, list) else []
    )
    raw_policies = raw_step.get("policies", [])
    policy_list: list[str] = (
        [str(p).strip() for p in raw_policies if str(p).strip()]
        if isinstance(raw_policies, list)
        else []
    )

    declares_intention = bool(raw_step.get("declares_intention", False))
    reverse_doc_from_code = bool(raw_step.get("reverse_doc_from_code", False))

    for plugin in get_workflow_policy_plugins():
        extra_tags, extra_policies = plugin.normalize_raw_step(raw_step)
        for et in extra_tags:
            if et not in tag_list:
                tag_list.append(et)
        for ep in extra_policies:
            if ep not in policy_list:
                policy_list.append(ep)

    for p_key in policy_list:
        if not is_registered_workflow_policy(p_key):
            findings.append(
                WorkflowValidationFinding(
                    line=line_of(raw_step, "policies", s_line),
                    rule_code="ERR_UNKNOWN_WORKFLOW_POLICY",
                    field_path=f"steps.{step_key}.policies",
                    message=yc["unknown_policy"].format(
                        line=line_of(raw_step, "policies", s_line),
                        policy=p_key,
                        step_key=step_key,
                    ),
                )
            )

    return WorkflowStepSpec(
        step_key=step_key,
        title=str(raw_step.get("title", step_key)).strip(),
        step_type=raw_type,  # type: ignore[arg-type]
        instructions=str(raw_step.get("instructions", "")).strip(),
        depends_on=depends_on,
        feedback_target_step_key=(
            str(raw_step["feedback_target_step_key"]).strip()
            if raw_step.get("feedback_target_step_key")
            else None
        ),
        max_agent_retries=max_retries,
        agent_uri=str(raw_step["agent_uri"]).strip() if raw_step.get("agent_uri") else None,
        skill_uri=str(raw_step["skill_uri"]).strip() if raw_step.get("skill_uri") else None,
        sub_workflow_uri=str(sub_wf_uri).strip() if isinstance(sub_wf_uri, str) else None,
        input_mapping=clean_str_dict(raw_step.get("input_mapping")),
        output_mapping=clean_str_dict(raw_step.get("output_mapping")),
        template_key=(
            str(raw_step["template_key"]).strip() if raw_step.get("template_key") else None
        ),
        kb_uris=kb_uris,
        human_authored_required=bool(raw_step.get("human_authored_required", False)),
        requires_human_gate=bool(raw_step.get("requires_human_gate", False)),
        declares_intention=declares_intention,
        reverse_doc_from_code=reverse_doc_from_code,
        tags=tuple(tag_list),
        policies=tuple(policy_list),
        verification_window_seconds=int(ver_win) if isinstance(ver_win, int) else None,
        line_number=s_line,
    )


__all__ = [
    "VALID_CRITICALITIES",
    "VALID_EXECUTION_REGIMES",
    "VALID_GATE_POLICIES",
    "VALID_MODES",
    "VALID_STEP_TYPES",
    "VALID_TIE_BREAK_POLICIES",
    "WorkflowPolicyPluginProtocol",
    "clean_str_dict",
    "get_valid_workflow_modes",
    "get_workflow_policy_plugins",
    "is_registered_workflow_policy",
    "line_of",
    "parse_raw_yaml_or_json",
    "parse_single_step_spec",
    "register_workflow_policy_plugin",
]
