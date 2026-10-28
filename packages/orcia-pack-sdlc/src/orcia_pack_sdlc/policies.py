"""SDLC Workflow Policy Plugin (`FR-13`: Intention -> Code & `brownfield_bootstrap`, `AD-20`)."""

from __future__ import annotations

from typing import Any

from orcia_core.orchestration.models import (
    WorkflowStepSpec,
    WorkflowValidationFinding,
)
from orcia_core.orchestration.yaml_loader import (
    WorkflowPolicyPluginProtocol,
    register_workflow_policy_plugin,
)


class SdlcFr13WorkflowPolicyPlugin(WorkflowPolicyPluginProtocol):
    """Enforces rule `FR-13` (`Intention -> Code` and `brownfield_bootstrap`)."""

    @property
    def policy_keys(self) -> tuple[str, ...]:
        return (
            "sdlc.fr13_intention_before_code",
            "sdlc.writes_code",
            "sdlc.declares_intention",
            "sdlc.reverse_doc_from_code",
            "sdlc.mode.brownfield_bootstrap",
        )

    @property
    def allowed_modes(self) -> tuple[str, ...]:
        return ("brownfield_bootstrap", "sdlc.mode.brownfield_bootstrap")

    def normalize_raw_step(
        self, raw_step: dict[str, Any]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Translate legacy `writes_code`, `declares_intention`, `reverse_doc_from_code` to tags."""
        tags: list[str] = []
        policies: list[str] = []
        if bool(raw_step.get("writes_code", False)):
            tags.append("sdlc.writes_code")
            policies.append("sdlc.fr13_intention_before_code")
        if bool(raw_step.get("declares_intention", False)):
            tags.append("sdlc.declares_intention")
        if bool(raw_step.get("reverse_doc_from_code", False)):
            tags.append("sdlc.reverse_doc_from_code")
            policies.append("sdlc.fr13_intention_before_code")
        return tuple(tags), tuple(policies)

    def validate_dag(
        self,
        parsed_steps: list[WorkflowStepSpec],
        steps_by_key: dict[str, WorkflowStepSpec],
        mode: str,
        findings: list[WorkflowValidationFinding],
    ) -> None:
        """Enforce `FR-13`: `sdlc.writes_code` requires upstream `sdlc.declares_intention`."""

        def _ancestors_of(key: str) -> set[str]:
            visited: set[str] = set()
            stack = list(steps_by_key[key].depends_on) if key in steps_by_key else []
            while stack:
                item = stack.pop()
                if item not in visited and item in steps_by_key:
                    visited.add(item)
                    stack.extend(steps_by_key[item].depends_on)
            return visited

        def _has_intent(step: WorkflowStepSpec) -> bool:
            return step.declares_intention or "sdlc.declares_intention" in step.tags

        for step in parsed_steps:
            writes_code = "sdlc.writes_code" in step.tags or "sdlc.writes_code" in step.policies
            if writes_code:
                ancestors = _ancestors_of(step.step_key)
                has_prior_intent = any(_has_intent(steps_by_key[a]) for a in ancestors)
                if not has_prior_intent and not _has_intent(step):
                    findings.append(
                        WorkflowValidationFinding(
                            line=step.line_number,
                            rule_code="ERR_INTENTION_BEFORE_CODE_REQUIRED",
                            field_path=f"steps.{step.step_key}.writes_code",
                            message=(
                                f"Ligne {step.line_number}: L'étape '{step.step_key}' modifie du "
                                "code ('writes_code: true') sans étape amont déclarant l'intention "
                                "('declares_intention: true') (FR-13)."
                            ),
                        )
                    )
            rev_doc = (
                step.reverse_doc_from_code
                or "sdlc.reverse_doc_from_code" in step.tags
                or "sdlc.reverse_doc_from_code" in step.policies
            )
            if rev_doc and mode not in ("brownfield_bootstrap", "sdlc.mode.brownfield_bootstrap"):
                findings.append(
                    WorkflowValidationFinding(
                        line=step.line_number,
                        rule_code="ERR_INTENTION_BEFORE_CODE_REQUIRED",
                        field_path=f"steps.{step.step_key}.reverse_doc_from_code",
                        message=(
                            f"Ligne {step.line_number}: L'étape '{step.step_key}' active "
                            "'reverse_doc_from_code: true' uniquement autorisé en mode "
                            "'brownfield_bootstrap' (FR-13)."
                        ),
                    )
                )


def create_sdlc_fr13_policy_plugin() -> SdlcFr13WorkflowPolicyPlugin:
    plugin = SdlcFr13WorkflowPolicyPlugin()
    register_workflow_policy_plugin("sdlc_fr13", plugin)
    return plugin
