"""Layer 1a unit & static audit tests for Story 24.2 (`REM24-03`, `REM24-04`, `USER24-BUG-6`)."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from orcia_core.gates import StarlarkMechanismSandbox
from orcia_core.orchestration import _triggers_lifecycle_ops as triggers_ops
from orcia_core.orchestration._dna_glossary_ops import (
    enforce_fifo_cap_15,
    execute_promote_or_reject_in_flow,
    execute_two_pass_glossary_extraction,
    term_fingerprint,
)
from orcia_core.orchestration._dna_starlark_compiler import (
    compile_starlark_from_natural_language,
    evaluate_starlark_mechanism_in_sandbox,
    validate_payload_against_schema,
)
from orcia_core.orchestration._dna_starlark_models import GlossaryCandidateItem
from orcia_core.orchestration._internal.sql_dna_mechanisms import (
    SqlStarlarkMechanismRepository,
    _parse_json_dict,
)
from orcia_core.orchestration._triggers_crud_helpers import CreateTriggerCommand
from orcia_core.orchestration._triggers_lifecycle_ops import execute_create_trigger
from orcia_core.orchestration.dna_starlark_and_glossary_lifecycle import (
    DnaStarlarkAndGlossaryLifecycleService,
)
from orcia_core.orchestration.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.orchestration.models import WorkflowTriggerEntity
from orcia_core.orchestration.triggers_dispatcher import TriggerDispatcherService
from orcia_core.orchestration.workspace_governance_and_rebaser import (
    WorkspaceGovernanceAndArtifactRoutingService,
)
from orcia_core.permissions import AutonomyContractService, HierarchicalRbacService
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    TriggerDuplicateKeyError,
)
from orcia_core.rag._internal.sql_rag_writes import (
    _format_halfvec_literal,
    parse_uuid_or_none,
)
from orcia_core.rag._internal.sql_state_queries import _parse_str_tuple
from orcia_core.rag._internal.sql_tripartite_writes import (
    upsert_kb_stale_alert_pg,
    upsert_tripartite_edges_pg,
)
from orcia_core.rag.models import KbStaleAlertEntity

REPO_ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_MOCK_WORKSPACE_LITERALS = ("default-ws", "ws-claims-alpha", "ws-mon-compte")


@pytest.mark.asyncio
async def test_execute_create_trigger_1000_sequential_same_millisecond_zero_collision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1 000 sequential `execute_create_trigger` calls with identical 8-char prefix -> 0 dupes."""
    counter = 0

    def _same_ms_uuid7() -> str:
        nonlocal counter
        counter += 1
        # Simulate identical 32-bit MSB timestamp prefix (`0195f000`) within the same ms
        return f"0195f000-0000-7000-8000-{counter:012x}"

    monkeypatch.setattr(triggers_ops, "new_uuid7_str", _same_ms_uuid7)

    cipher = PassthroughVaultCipher("0" * 32)
    triggers_mem: dict[str, WorkflowTriggerEntity] = {}
    secrets_mem: dict[str, str] = {}
    keys: list[str] = []

    for _ in range(1000):
        entity = await execute_create_trigger(
            cmd=CreateTriggerCommand(
                workspace_id="0195f000-0000-7000-8000-000000000301",
                workflow_id="wf-01-qualification-prd",
                trigger_type="LOG_SINK_ALERT",
                log_sink_service="orcia-api",
            ),
            contract=None,
            cipher=cipher,
            repo=None,
            triggers_mem=triggers_mem,
            secrets_mem=secrets_mem,
        )
        keys.append(entity.trigger_key)

    assert len(keys) == 1000
    assert len(set(keys)) == 1000
    assert all(k.startswith("trg-log_sink_alert-") for k in keys)


@pytest.mark.asyncio
async def test_execute_create_trigger_real_uuid7_1000_burst_and_duplicate_explicit_key() -> None:
    """Real UUIDv7 burst of 1 000 creations produces 1 000 unique keys; dup key raises 409."""
    cipher = PassthroughVaultCipher("0" * 32)
    triggers_mem: dict[str, WorkflowTriggerEntity] = {}
    secrets_mem: dict[str, str] = {}

    for _ in range(1000):
        await execute_create_trigger(
            cmd=CreateTriggerCommand(
                workspace_id="0195f000-0000-7000-8000-000000000301",
                workflow_id="wf-01-qualification-prd",
                trigger_type="MANUAL_AUTONOMOUS",
            ),
            contract=None,
            cipher=cipher,
            repo=None,
            triggers_mem=triggers_mem,
            secrets_mem=secrets_mem,
        )
    assert len({t.trigger_key for t in triggers_mem.values()}) == 1000

    first = await execute_create_trigger(
        cmd=CreateTriggerCommand(
            workspace_id="0195f000-0000-7000-8000-000000000301",
            workflow_id="wf-01-qualification-prd",
            trigger_type="LOG_SINK_ALERT",
            trigger_key="alert-api-500",
        ),
        contract=None,
        cipher=cipher,
        repo=None,
        triggers_mem=triggers_mem,
        secrets_mem=secrets_mem,
    )
    assert first.trigger_key == "alert-api-500"

    with pytest.raises(TriggerDuplicateKeyError) as exc_info:
        await execute_create_trigger(
            cmd=CreateTriggerCommand(
                workspace_id="0195f000-0000-7000-8000-000000000301",
                workflow_id="wf-01-qualification-prd",
                trigger_type="LOG_SINK_ALERT",
                trigger_key="alert-api-500",
            ),
            contract=None,
            cipher=cipher,
            repo=None,
            triggers_mem=triggers_mem,
            secrets_mem=secrets_mem,
        )
    assert exc_info.value.http_status == 409
    assert exc_info.value.error_code == "ERR_TRIGGER_DUPLICATE_KEY"


@pytest.mark.asyncio
async def test_dna_starlark_split_compiler_sandbox_and_strict_sql_fail_closed() -> None:
    """Verify `_dna_starlark_compiler`, sandbox evaluation, and `strict_sql=True` fail-closed."""
    sandbox = StarlarkMechanismSandbox()
    ws_id = uuid4()

    with pytest.raises(ValidationDomainError, match="missing required schema key"):
        validate_payload_against_schema({"other": "1"}, {"required": ["reference_code"]})

    with pytest.raises(ObserverModeReadOnlyError):
        compile_starlark_from_natural_language(
            sandbox,
            actor_role="READ_ONLY_OBSERVER",
            rule_id="RULE_OBS",
            directive_title="Directive",
            norm_title="Norm",
            natural_language_rule_fr="Doit bloquer",
            target_json_schema={},
            required_field="reference_code",
        )

    mech = compile_starlark_from_natural_language(
        sandbox,
        actor_role="TEAM_LEAD",
        rule_id="RULE_REF_CODE",
        directive_title="Qualité",
        norm_title="Code Référence",
        natural_language_rule_fr="Le champ reference_code doit être valide.",
        target_json_schema={"required": ["reference_code"]},
        required_field="reference_code",
        simulate_initial_bad_regex=True,
        workspace_id=ws_id,
    )
    assert mech.self_corrected is True
    assert mech.workspace_id == ws_id
    assert mech.signed_and_active is True

    # Failure when failing payload cannot even fail or pass payload fails both retries
    with pytest.raises(ValidationDomainError):
        compile_starlark_from_natural_language(
            sandbox,
            actor_role="TEAM_LEAD",
            rule_id="RULE_BAD",
            directive_title="Qualité",
            norm_title="Bad",
            natural_language_rule_fr="Impossible",
            target_json_schema={},
            required_field="reference_code",
            passing_test_payload={"reference_code": "invalid value!"},
            failing_test_payload={"reference_code": "invalid value!"},
        )

    eval_pass = evaluate_starlark_mechanism_in_sandbox(
        sandbox,
        mechanism=mech,
        mechanism_id=mech.mechanism_id,
        payload={"reference_code": "ORCIA_24_2"},
    )
    assert eval_pass.passed is True
    assert eval_pass.llm_tokens_consumed == 0

    eval_fail = evaluate_starlark_mechanism_in_sandbox(
        sandbox,
        mechanism=mech,
        mechanism_id=mech.mechanism_id,
        payload={"reference_code": "bad!"},
    )
    assert eval_fail.passed is False
    assert eval_fail.staged_effects[0].staged_only is True

    with pytest.raises(ValidationDomainError, match="Unknown Starlark mechanism"):
        evaluate_starlark_mechanism_in_sandbox(
            sandbox,
            mechanism=None,
            mechanism_id=uuid4(),
            payload={},
        )

    # Service with strict_sql=True and no repository fails closed on all async PG18 methods
    strict_svc = DnaStarlarkAndGlossaryLifecycleService(repository=None, strict_sql=True)
    with pytest.raises(RuntimeError, match="strict_sql=True"):
        await strict_svc.compile_from_natural_language_async(
            workspace_id=ws_id,
            actor_role="PLATFORM_ADMIN",
            rule_id="RULE_STRICT",
            directive_title="Strict",
            norm_title="Strict",
            natural_language_rule_fr="Exige PG18.",
            target_json_schema={},
            required_field="reference_code",
        )
    with pytest.raises(RuntimeError, match="strict_sql=True"):
        await strict_svc.list_mechanisms_for_workspace_async(workspace_id=ws_id)
    with pytest.raises(RuntimeError, match="strict_sql=True"):
        await strict_svc.activate_mechanism_async(
            workspace_id=ws_id,
            mechanism_id=mech.mechanism_id,
            actor_role="PLATFORM_ADMIN",
        )
    with pytest.raises(RuntimeError, match="strict_sql=True"):
        await strict_svc.evaluate_runtime_mechanism_async(
            workspace_id=ws_id,
            mechanism_id=mech.mechanism_id,
            payload={},
        )

    # Non-strict memory service supports async list/activate & proper error handling
    mem_svc = DnaStarlarkAndGlossaryLifecycleService()
    saved = await mem_svc.compile_from_natural_language_async(
        workspace_id=ws_id,
        actor_role="TEAM_LEAD",
        rule_id="RULE_MEM",
        directive_title="Mem",
        norm_title="Mem",
        natural_language_rule_fr="Test mémoire.",
        target_json_schema={},
        required_field="reference_code",
    )
    assert len(await mem_svc.list_mechanisms_for_workspace_async(workspace_id=ws_id)) == 1
    activated = await mem_svc.activate_mechanism_async(
        workspace_id=ws_id,
        mechanism_id=saved.mechanism_id,
        actor_role="TEAM_LEAD",
    )
    assert activated.signed_and_active is True
    with pytest.raises(ObserverModeReadOnlyError):
        await mem_svc.activate_mechanism_async(
            workspace_id=ws_id,
            mechanism_id=saved.mechanism_id,
            actor_role="READ_ONLY_OBSERVER",
        )
    with pytest.raises(ResourceNotFoundError):
        await mem_svc.activate_mechanism_async(
            workspace_id=ws_id,
            mechanism_id=uuid4(),
            actor_role="TEAM_LEAD",
        )

    # Governance service strict_sql=True fails closed without session_factory
    gov_strict = WorkspaceGovernanceAndArtifactRoutingService(session_factory=None, strict_sql=True)
    with pytest.raises(RuntimeError, match="session_factory"):
        await gov_strict.list_exception_waivers_async(workspace_id=ws_id)
    tabs_state = gov_strict.get_workspace_five_tabs_state(workspace_id=ws_id)
    assert tabs_state.workspace_slug == str(ws_id)


def test_dna_glossary_ops_two_pass_fifo_and_in_flow_promotion() -> None:
    """Verify `_dna_glossary_ops` 2-pass extraction, TTL purge, FIFO 15, Top-3 & In-Flow."""
    ws_id = uuid4()
    now = datetime.now(UTC)
    expired_item = GlossaryCandidateItem(
        candidate_id=uuid4(),
        workspace_id=ws_id,
        canonical_term="Ancien Terme Expiré",
        fingerprint=term_fingerprint("Ancien Terme Expiré"),
        definition_fr="Ancienne définition",
        confidence_score=0.7,
        level="4_RUN_EPHEMERAL",
        status="PENDING_VALIDATION",
        ontology_conflict_warning=None,
        pre_checked_for_in_flow_promotion=False,
        created_at=now - timedelta(days=31),
    )
    queue: list[GlossaryCandidateItem] = [expired_item]
    active_map: dict[str, str] = {}
    rejected_set: set[str] = set()
    cache_counter: dict[object, int] = {}

    # Pass 1 on git_push: 0 LLM calls, purges >30d item
    res_git = execute_two_pass_glossary_extraction(
        workspace_id=ws_id,
        trigger_type="git_push",
        raw_candidates=[("Terme Push", "Définition AST", 0.9)],
        active_map=active_map,
        rejected_set=rejected_set,
        queue=queue,
        now=now,
    )
    assert res_git.pass_1_deterministic_executed is True
    assert res_git.pass_2_llm_batch_executed is False
    assert res_git.llm_calls_count == 0
    assert res_git.purged_expired_ephemeral_count == 1
    assert res_git.top3_in_flow_prechecked == ()

    # Pass 2 on mr_pr: detects ONTOLOGY_CONFLICT, enforces FIFO <= 15 & Top-3 pre-checked
    batch = [(f"Terme {i}", f"Def {i}", 0.86 + (i * 0.005)) for i in range(18)]
    batch.append(("Terme Conflit", "Définition divergente", 0.99))
    res_mr = execute_two_pass_glossary_extraction(
        workspace_id=ws_id,
        trigger_type="mr_pr",
        raw_candidates=batch,
        active_map=active_map,
        rejected_set=rejected_set,
        queue=queue,
        existing_enterprise_terms={"Terme Conflit": "Définition officielle entreprise"},
        now=now,
    )
    assert res_mr.pass_2_llm_batch_executed is True
    assert res_mr.llm_calls_count == 1
    assert len(res_mr.active_queue_candidates) <= 15
    assert len(res_mr.top3_in_flow_prechecked) == 3
    assert all(c.ontology_conflict_warning is None for c in res_mr.top3_in_flow_prechecked)

    # FIFO helper unit verification
    enforce_fifo_cap_15(queue)
    assert len(queue) <= 15

    # In-Flow promotion & rejection
    with pytest.raises(ObserverModeReadOnlyError):
        execute_promote_or_reject_in_flow(
            workspace_id=ws_id,
            actor_role="READ_ONLY_OBSERVER",
            promote_candidate_ids=[],
            reject_candidate_ids=[],
            queue=queue,
            active_map=active_map,
            rejected_set=rejected_set,
            cache_invalidation_counter=cache_counter,  # type: ignore[arg-type]
        )

    to_promote = [res_mr.top3_in_flow_prechecked[0].candidate_id]
    conflict_candidates = [c for c in queue if c.ontology_conflict_warning]
    if conflict_candidates:
        to_promote.append(conflict_candidates[0].candidate_id)
    to_reject = [res_mr.top3_in_flow_prechecked[1].candidate_id]
    rejected_term = res_mr.top3_in_flow_prechecked[1].canonical_term

    promo = execute_promote_or_reject_in_flow(
        workspace_id=ws_id,
        actor_role="TEAM_LEAD",
        promote_candidate_ids=to_promote,
        reject_candidate_ids=to_reject,
        queue=queue,
        active_map=active_map,
        rejected_set=rejected_set,
        cache_invalidation_counter=cache_counter,  # type: ignore[arg-type]
    )
    assert promo.assistant_prompt_cache_invalidated is True
    assert cache_counter[ws_id] == 1
    assert rejected_term in promo.rejected_terms
    assert term_fingerprint(rejected_term) in rejected_set
    if conflict_candidates:
        assert len(promo.what_if_impact_warnings) == 1

    # Re-extracting rejected term does not re-queue it
    res_retry = execute_two_pass_glossary_extraction(
        workspace_id=ws_id,
        trigger_type="manual_sync",
        raw_candidates=[(rejected_term, "Nouvelle tentative", 0.99)],
        active_map=active_map,
        rejected_set=rejected_set,
        queue=queue,
        now=now,
    )
    assert all(c.canonical_term != rejected_term for c in res_retry.active_queue_candidates)


def test_zero_legacy_dummy_workspace_slugs_in_runtime_code() -> None:
    """Static audit: 0 occurrence of `default-ws`, `ws-claims-alpha`, `ws-mon-compte` in runtime."""
    excluded_dirs = {"__tests__", "tests", "__pycache__", "node_modules", "dist", "generated"}
    pattern = re.compile("|".join(re.escape(lit) for lit in FORBIDDEN_MOCK_WORKSPACE_LITERALS))
    violations: list[str] = []

    for root_name in ("apps", "packages", "infra"):
        root_path = REPO_ROOT / root_name
        if not root_path.exists():
            continue
        for file_path in root_path.rglob("*"):
            if not file_path.is_file():
                continue
            if any(part in excluded_dirs for part in file_path.parts):
                continue
            if file_path.name == "openapi.json":
                continue
            allowed_ext = {".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".yaml", ".yml"}
            if file_path.suffix not in allowed_ext:
                continue
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for idx, line in enumerate(content.splitlines(), start=1):
                if pattern.search(line):
                    rel = file_path.relative_to(REPO_ROOT)
                    violations.append(f"{rel}:{idx}: {line.strip()}")

    assert violations == [], "Forbidden dummy workspace slugs found:\n" + "\n".join(violations)


def test_sql_dna_mechanisms_helpers_and_guards() -> None:
    """Verify `_parse_json_dict` edge cases and `SqlStarlarkMechanismRepository` fail-closed."""
    assert _parse_json_dict('{"a": 1}') == {"a": 1}
    assert _parse_json_dict("[1, 2]") == {}
    assert _parse_json_dict({"b": 2}) == {"b": 2}
    assert _parse_json_dict(None) == {}

    repo_unconfigured = SqlStarlarkMechanismRepository()
    with pytest.raises(RuntimeError, match="PG18 engine/session"):
        repo_unconfigured._require_session_maker()

    assert _parse_str_tuple('["run-1", "run-2"]') == ("run-1", "run-2")
    assert _parse_str_tuple(["run-3"]) == ("run-3",)
    assert _parse_str_tuple(None) == ()


@pytest.mark.asyncio
async def test_record_alert_delivery_async_in_memory_dedup() -> None:
    """Verify `record_alert_delivery_async` deduplicates identical alert delivery keys."""
    contracts = AutonomyContractService(rbac_service=HierarchicalRbacService())
    svc = TriggerDispatcherService(contract_service=contracts)
    first = await svc.record_alert_delivery_async(
        trigger_id="0195f000-0000-7000-8000-000000000901",
        delivery_key="alert:fp-001",
    )
    second = await svc.record_alert_delivery_async(
        trigger_id="0195f000-0000-7000-8000-000000000901",
        delivery_key="alert:fp-001",
    )
    assert first is True
    assert second is False


@pytest.mark.asyncio
async def test_sql_rag_and_tripartite_writes_pure_helpers_and_guards() -> None:
    """Verify `sql_rag_writes` / `sql_tripartite_writes` pure helpers & invalid UUID guards."""
    assert parse_uuid_or_none(None) is None
    assert parse_uuid_or_none("not-a-uuid") is None
    assert (
        parse_uuid_or_none("0195f000-0000-7000-8000-000000000001")
        == "0195f000-0000-7000-8000-000000000001"
    )
    vec = _format_halfvec_literal((0.5, -0.25), dim=4)
    assert vec == "[0.500000,-0.250000,0.000000,0.000000]"

    assert await upsert_tripartite_edges_pg(None, edges=()) == ()  # type: ignore[arg-type]
    missing = await upsert_kb_stale_alert_pg(
        None,  # type: ignore[arg-type]
        alert=KbStaleAlertEntity(
            id="0195f000-0000-7000-8000-000000000999",
            alert_key="a-invalid",
            workspace_id="not-a-uuid",
            document_key="doc-missing",
            source_uri="confluence://missing",
            alert_reason="TTL_EXPIRED",
            diagnostic_marker="[STALE_WARNING]",
            justifying_jira_key=None,
            impacted_run_ids=(),
            resolved=False,
        ),
    )
    assert missing is None
