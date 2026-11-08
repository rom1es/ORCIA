"""Unit tests for TASK-04 (`tests/unit/core/test_generic_gate_runners_and_auto_heal.py`).

Validates:
- The 4 generic deterministic gate runners (`markdown_contract_runner`, `json_schema_runner`,
  `cli_sandbox_runner`, `catalog_invariant_runner`).
- `GatePipelineExecutor` deterministic-first inviolability (`ADR-06`, `CA-9.4.1`): probabilistic
  *Hunters* are never invoked (`0` calls) when deterministic controls fail.
- Bounded self-healing loop (`max_self_heal_retries = 3`, `CA-9.4.2`) in `NATIVE_ORCIA` mode.
"""

from __future__ import annotations

from orcia_core.workflows.gates import (
    GatePipelineExecutor,
    ProbabilisticControlExecutionRecord,
    catalog_invariant_runner,
    cli_sandbox_runner,
    json_schema_runner,
    markdown_contract_runner,
)
from orcia_core.workflows.schemas_v2 import (
    DeterministicControlSpec,
    ExecutionMode,
    GateExecutionStrategy,
    NonDeterministicControlSpec,
    StepControlsPipeline,
)


def test_four_generic_deterministic_runners() -> None:
    """Verify each of the 4 generic deterministic runners on valid and invalid inputs."""
    # 1. markdown_contract_runner
    md_config = {
        "required_headings": ["# Étude", "## Scénarios"],
        "min_chars_per_section": 15,
        "require_mermaid_blocks": 1,
        "forbid_patterns": ["TODO", "TBD"],
    }
    valid_md = (
        "# Étude\nDescription détaillée du contexte métier.\n\n"
        "## Scénarios\nComparaison approfondie des options.\n"
        "```mermaid\nflowchart LR\n  A --> B\n```\n"
    )
    assert markdown_contract_runner(valid_md, md_config).status == "NOMINAL"

    invalid_md = "# Étude\nTrop court TODO"
    md_fail = markdown_contract_runner(invalid_md, md_config)
    assert md_fail.status == "FAILED"
    assert len(md_fail.violations) >= 3

    # 2. json_schema_runner
    schema_cfg = {
        "required_fields": ["title", "effort"],
        "properties": {"title": {"type": "string"}, "effort": {"type": "integer"}},
        "strict_additional_properties": True,
    }
    assert json_schema_runner('{"title": "Lot 1", "effort": 5}', schema_cfg).status == "NOMINAL"
    assert (
        json_schema_runner('{"title": "Lot 1", "effort": "bad", "extra": 1}', schema_cfg).status
        == "FAILED"
    )

    # 3. cli_sandbox_runner
    assert cli_sandbox_runner("clean code", {"command": "ruff check"}).status == "NOMINAL"
    assert (
        cli_sandbox_runner("code with SYNTAX_ERROR", {"command": "ruff check"}).status == "FAILED"
    )

    # 4. catalog_invariant_runner
    cat_cfg = {
        "allowed_classifications": ["INTERNAL", "RESTRICTED"],
        "classification": "INTERNAL",
        "require_existing_entities": True,
        "known_entities": ["catalog://tracker/item/101"],
    }
    assert (
        catalog_invariant_runner("Référence catalog://tracker/item/101 valide", cat_cfg).status
        == "NOMINAL"
    )
    assert (
        catalog_invariant_runner("Référence catalog://tracker/item/999 inconnue", cat_cfg).status
        == "FAILED"
    )


def test_gate_pipeline_bounded_auto_heal_then_hunter_execution() -> None:
    """Verify deterministic control self-heals on retry #2 and then runs Hunter (`CA-9.4.2`)."""
    pipeline = StepControlsPipeline(
        strategy=GateExecutionStrategy.FAIL_FAST,
        deterministic=[
            DeterministicControlSpec(
                id="det-md",
                name="Contrat Markdown",
                short_label="Markdown",
                runner_plugin_id="markdown_contract_runner",
                verifies_description="Sections obligatoires présentes",
                on_ko_behavior="Auto-remédiation 3x",
                max_self_heal_retries=3,
                config={
                    "required_headings": ["# Dossier", "## Décisions"],
                    "min_chars_per_section": 15,
                    "forbid_patterns": ["TODO"],
                },
            )
        ],
        non_deterministic=[
            NonDeterministicControlSpec(
                id="ndet-hunter",
                name="Contradicteur",
                short_label="Hunter",
                evaluator_type="adversarial_agent",
                agent_ref="pack://domain/gates/hunter",
                risk_threshold=0.70,
                verifies_description="Revue contradictoire",
                on_ko_behavior="Escalade Anchor Card",
            )
        ],
    )

    heal_calls: list[int] = []
    hunter_calls: list[str] = []

    def fake_self_heal(current_text: str, stderr: str, retry_num: int) -> str:
        heal_calls.append(retry_num)
        assert "Missing required heading" in stderr or "Forbidden pattern" in stderr
        if retry_num < 2:
            return "# Dossier\nContenu suffisant mais encore TODO."
        return (
            "# Dossier\nDescription complète et validée.\n\n"
            "## Décisions\nArbitrages documentés sans marqueur interdit.\n"
        )

    def fake_hunter(
        spec: NonDeterministicControlSpec, artifact: str
    ) -> ProbabilisticControlExecutionRecord:
        hunter_calls.append(spec.id)
        return ProbabilisticControlExecutionRecord(
            control_id=spec.id,
            agent_ref=spec.agent_ref,
            status="NOMINAL",
            risk_score=0.12,
            findings=["Aucune contradiction détectée."],
        )

    executor = GatePipelineExecutor()
    report = executor.execute_pipeline(
        pipeline=pipeline,
        artifact_text="# Brouillon incomplet TODO",
        execution_mode=ExecutionMode.NATIVE_ORCIA,
        self_heal_callback=fake_self_heal,
        hunter_callback=fake_hunter,
    )

    assert report.overall_status == "NOMINAL"
    assert report.deterministic_passed is True
    assert report.probabilistic_invoked is True
    assert report.total_self_heal_retries_used == 2
    assert heal_calls == [1, 2]
    assert hunter_calls == ["ndet-hunter"]
    assert report.deterministic_records[0].self_healed is True
    assert report.deterministic_records[0].attempts == 3


def test_gate_pipeline_deterministic_failure_never_invokes_probabilistic_hunters() -> None:
    """Verify ADR-06 (`CA-9.4.1`): when deterministic gate fails after 3 retries, 0 Hunters run."""
    pipeline = StepControlsPipeline(
        strategy=GateExecutionStrategy.FAIL_FAST,
        deterministic=[
            DeterministicControlSpec(
                id="det-strict",
                name="Contrat Strict",
                short_label="Strict",
                runner_plugin_id="markdown_contract_runner",
                verifies_description="Exige # Titre Officiel",
                on_ko_behavior="Stop",
                max_self_heal_retries=3,
                config={"required_headings": ["# Titre Officiel"]},
            )
        ],
        non_deterministic=[
            NonDeterministicControlSpec(
                id="ndet-never-called",
                name="Hunter Coûteux",
                short_label="Hunter",
                evaluator_type="adversarial_agent",
                agent_ref="pack://domain/gates/hunter",
                verifies_description="Ne doit jamais tourner si déterministe KO",
                on_ko_behavior="Escalade",
            )
        ],
    )

    hunter_invocations = 0

    def broken_self_heal(current_text: str, _stderr: str, retry_num: int) -> str:
        return f"{current_text}\nEssai {retry_num} toujours sans le bon titre."

    def forbidden_hunter(
        spec: NonDeterministicControlSpec, _artifact: str
    ) -> ProbabilisticControlExecutionRecord:
        nonlocal hunter_invocations
        hunter_invocations += 1
        return ProbabilisticControlExecutionRecord(
            control_id=spec.id,
            agent_ref=spec.agent_ref,
            status="NOMINAL",
            risk_score=0.0,
        )

    executor = GatePipelineExecutor()
    report = executor.execute_pipeline(
        pipeline=pipeline,
        artifact_text="Texte invalide",
        execution_mode=ExecutionMode.NATIVE_ORCIA,
        self_heal_callback=broken_self_heal,
        hunter_callback=forbidden_hunter,
    )

    assert report.overall_status == "FAILED_DETERMINISTIC"
    assert report.deterministic_passed is False
    assert report.probabilistic_invoked is False
    assert report.total_self_heal_retries_used == 3
    assert hunter_invocations == 0
    assert report.probabilistic_records == []
