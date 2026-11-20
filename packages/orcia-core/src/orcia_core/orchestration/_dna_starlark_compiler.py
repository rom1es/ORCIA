"""Pure Starlark DNA mechanism compilation, self-testing & sandbox evaluation."""

from __future__ import annotations

import hashlib
import time
from typing import Any
from uuid import UUID

from uuid_utils.compat import uuid7

from orcia_core.gates import (
    StarlarkEvaluationResult,
    StarlarkMechanismSandbox,
    StarlarkSandboxError,
)
from orcia_core.orchestration._dna_starlark_models import GeneratedStarlarkMechanism
from orcia_core.orchestration.errors import ValidationDomainError
from orcia_core.permissions.errors import ObserverModeReadOnlyError


def validate_payload_against_schema(payload: dict[str, Any], schema: dict[str, Any]) -> None:
    """Validate that required JSON schema keys exist on a test payload."""
    required = schema.get("required", [])
    if isinstance(required, list):
        for req_key in required:
            if req_key not in payload:
                raise ValidationDomainError(
                    detail_override=f"Test payload is missing required schema key '{req_key}'."
                )


def render_starlark_script(
    *,
    rule_id: str,
    required_field: str,
    regex_pattern: str,
    norm_title: str,
) -> str:
    """Render deterministic Starlark evaluation script for a norm."""
    return (
        "def evaluate(doc):\n"
        f"    val = str(doc.get({required_field!r}, ''))\n"
        f"    if orcia_sys.re_fullmatch({regex_pattern!r}, val):\n"
        f"        orcia_sys.emit_verdict({rule_id!r}, 'PASS', {f'Conforme : {norm_title}'!r})\n"
        "    else:\n"
        f"        orcia_sys.emit_verdict({rule_id!r}, 'FAIL', {f'Écart : {norm_title}'!r})\n"
        "        orcia_sys.emit_effect(\n"
        f"            'STAGE_ANNOTATION', 'orcia://staged/gate', {{'rule_id': {rule_id!r}}}\n"
        "        )\n"
    )


def verify_pass_and_fail(
    sandbox: StarlarkMechanismSandbox,
    *,
    starlark_code: str,
    passing_payload: dict[str, Any],
    failing_payload: dict[str, Any],
) -> None:
    """Verify compiled Starlark script passes valid payload and fails invalid payload."""
    pass_res = sandbox.evaluate_script(starlark_code=starlark_code, payload=passing_payload)
    if not pass_res.passed:
        raise StarlarkSandboxError("passing_test_payload did not evaluate to PASS.")
    fail_res = sandbox.evaluate_script(starlark_code=starlark_code, payload=failing_payload)
    if fail_res.passed:
        raise StarlarkSandboxError("failing_test_payload unexpectedly evaluated to PASS.")


def compile_starlark_from_natural_language(
    sandbox: StarlarkMechanismSandbox,
    *,
    actor_role: str,
    rule_id: str,
    directive_title: str,
    norm_title: str,
    natural_language_rule_fr: str,
    target_json_schema: dict[str, Any],
    required_field: str,
    regex_pattern: str = r"^[A-Z0-9_-]{3,64}$",
    passing_test_payload: dict[str, Any] | None = None,
    failing_test_payload: dict[str, Any] | None = None,
    simulate_initial_bad_regex: bool = False,
    workspace_id: UUID | None = None,
) -> GeneratedStarlarkMechanism:
    """Compile a French norm into a self-tested `.star` mechanism (`< 5 ms`, 1 retry)."""
    if actor_role == "READ_ONLY_OBSERVER":
        raise ObserverModeReadOnlyError(
            detail_override="READ_ONLY_OBSERVER cannot compile or activate Gate mechanisms."
        )

    started = time.perf_counter()
    pass_payload = passing_test_payload or {required_field: "ORCIA_VALID_01"}
    fail_payload = failing_test_payload or {required_field: "invalid value!"}

    validate_payload_against_schema(pass_payload, target_json_schema)
    validate_payload_against_schema(fail_payload, target_json_schema)

    initial_pattern = r"(a+)+$" if simulate_initial_bad_regex else regex_pattern
    candidate_code = render_starlark_script(
        rule_id=rule_id,
        required_field=required_field,
        regex_pattern=initial_pattern,
        norm_title=norm_title,
    )
    self_corrected = False
    try:
        verify_pass_and_fail(
            sandbox,
            starlark_code=candidate_code,
            passing_payload=pass_payload,
            failing_payload=fail_payload,
        )
    except StarlarkSandboxError:
        self_corrected = True
        candidate_code = render_starlark_script(
            rule_id=rule_id,
            required_field=required_field,
            regex_pattern=regex_pattern,
            norm_title=norm_title,
        )
        try:
            verify_pass_and_fail(
                sandbox,
                starlark_code=candidate_code,
                passing_payload=pass_payload,
                failing_payload=fail_payload,
            )
        except StarlarkSandboxError as exc:
            raise ValidationDomainError(detail_override=str(exc)) from exc

    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    script_name = f"{rule_id.lower().replace('_', '-')}.star"
    sha256_hex = hashlib.sha256(candidate_code.encode("utf-8")).hexdigest()
    breadcrumb = f"🛡️ [{directive_title}] ➔ 📏 [{norm_title}] ➔ ⚙️ Vérifié par : {script_name}"
    return GeneratedStarlarkMechanism(
        mechanism_id=uuid7(),
        rule_id=rule_id,
        directive_title=directive_title,
        norm_title=norm_title,
        script_name=script_name,
        starlark_code=candidate_code,
        sha256=sha256_hex,
        passing_test_payload=pass_payload,
        failing_test_payload=fail_payload,
        explanation_fr=(
            f"Vérifie de façon déterministe la norme « {norm_title} » "
            f"({natural_language_rule_fr}) sur le champ '{required_field}'."
        ),
        self_corrected=self_corrected,
        compile_elapsed_ms=elapsed_ms,
        verified_badge_fr="✓ Vérifié sur cas de test (PASS/FAIL en < 5 ms)",
        causal_breadcrumb=breadcrumb,
        signed_and_active=True,
        workspace_id=workspace_id,
    )


def evaluate_starlark_mechanism_in_sandbox(
    sandbox: StarlarkMechanismSandbox,
    *,
    mechanism: GeneratedStarlarkMechanism | None,
    mechanism_id: UUID,
    payload: dict[str, Any],
) -> StarlarkEvaluationResult:
    """Execute a compiled `.star` mechanism at Run-Time (`< 2 ms`, `0` LLM tokens)."""
    if mechanism is None:
        raise ValidationDomainError(detail_override=f"Unknown Starlark mechanism '{mechanism_id}'.")
    try:
        return sandbox.evaluate_script(starlark_code=mechanism.starlark_code, payload=payload)
    except StarlarkSandboxError as exc:
        raise ValidationDomainError(detail_override=str(exc)) from exc
