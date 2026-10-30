"""Story 4.1 tests: Tier 1 Sandbox, Pattern Drift, `init-existing-project` & `init-skill`."""

from __future__ import annotations

import os
import pathlib
import shutil
import time

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from orcia_api.main import create_app
from orcia_core.gates import (
    DeterministicGateFailedError,
    DeterministicGateInput,
    DeterministicGateService,
    OntologyAxiomCheckRule,
    PatternDriftDetectedError,
    PolicyDeniedError,
    UpstreamTimeoutError,
)
from orcia_core.orchestration.step_executors import SkillStepExecutor
from orcia_kernel.ports import StepExecutorContext

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKSPACE_ID = "0192c4e0-0000-7000-8000-000000000201"
RUN_ID = "0192c4e0-0000-7000-8000-000000003101"
STEP_EXEC_ID = "0192c4e0-0000-7000-8000-000000003201"


def test_story_4_1_migration_0017_real_postgres_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify migration `0017_story_4_1` (`gate_evaluations`) on real PostgreSQL 18 container."""
    monkeypatch.setenv("TESTCONTAINERS_RYUK_DISABLED", "true")
    suffix = f"tc_4_1_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    sock_dir = REPO_ROOT / ".pytest_cache" / suffix
    sock_dir.mkdir(parents=True, exist_ok=True)
    sock_dir.chmod(0o777)

    pg_container = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "orcia")
        .with_volume_mapping(str(sock_dir), "/var/run/postgresql", "rw")
    )
    try:
        with pg_container as pg:
            wait_for_logs(pg, "database system is ready to accept connections", timeout=30)
            sock_file = sock_dir / ".s.PGSQL.5432"
            for _ in range(40):
                if sock_file.exists():
                    break
                time.sleep(0.2)

            creds = "orcia:orcia_dev_secret"  # pragma: allowlist secret
            sync_url = f"postgresql+psycopg://{creds}@/orcia?host={sock_dir}"
            monkeypatch.setenv("DATABASE_URL", sync_url)
            alembic_cfg = Config(str(REPO_ROOT / "infra" / "migrations" / "alembic.ini"))
            alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
            alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

            engine = sa.create_engine(sync_url)
            for _ in range(30):
                try:
                    with engine.connect() as c:
                        c.execute(sa.text("SELECT 1"))
                    break
                except Exception:
                    time.sleep(0.2)

            command.upgrade(alembic_cfg, "0017_story_4_1")

            with engine.begin() as conn:
                cols = list(
                    conn.execute(
                        sa.text(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_name = 'gate_evaluations' ORDER BY ordinal_position"
                        )
                    ).scalars()
                )
                assert "gate_type" in cols
                assert "sandbox_tier" in cols
                assert "pattern_drift_passed" in cols
                assert "pattern_drift_findings_jsonb" in cols
                assert "briefing_4blocks_jsonb" in cols

            command.downgrade(alembic_cfg, "0016_story_3_5")
            command.upgrade(alembic_cfg, "0017_story_4_1")
            engine.dispose()
    finally:
        shutil.rmtree(sock_dir, ignore_errors=True)


def test_story_4_1_sandbox_tier1_pass_and_pattern_drift_detection() -> None:
    """Verify Tier 1 Sandbox checks schema, ontology axioms, and Pattern Drift (`FR-17`)."""
    svc = DeterministicGateService()

    # 1. Valid artifact passes all 3 checks and publishes GateEvaluated to Outbox
    pass_eval = svc.evaluate_deterministic_gate(
        DeterministicGateInput(
            workspace_id=WORKSPACE_ID,
            run_id=RUN_ID,
            step_execution_id=STEP_EXEC_ID,
            step_key="validate-architecture",
            artifact_payload={
                "artifact": "Spécification conforme PostgreSQL 18 + SeaweedFS S3",
                "dependencies": ["fastapi>=0.115.0", "pydantic>=2.11.0", "dbos"],
            },
            required_sections=("artifact",),
            ontology_axioms=(
                OntologyAxiomCheckRule(
                    axiom_key="ax-storage",
                    forbidden_term="minio/minio",
                    required_term="seaweedfs",
                ),
            ),
        ),
        raise_on_failure=True,
    )
    assert pass_eval.status == "PASS"
    assert pass_eval.score == 1.0
    assert pass_eval.schema_validation_passed is True
    assert pass_eval.ontology_axioms_passed is True
    assert pass_eval.pattern_drift_passed is True
    assert len(svc.list_outbox_events()) == 1
    assert svc.list_outbox_events()[0].event_type == "GateEvaluated"
    assert svc.list_outbox_events()[0].passed is True

    # 2. Pattern Drift detection (unapproved dependency + forbidden sqlite:// pattern)
    drift_eval = svc.evaluate_deterministic_gate(
        DeterministicGateInput(
            workspace_id=WORKSPACE_ID,
            run_id=RUN_ID,
            step_execution_id=STEP_EXEC_ID,
            step_key="validate-drift",
            artifact_payload={
                "artifact": "Connexion sqlite:///:memory: avec next/navigation",
                "dependencies": ["celery==5.4.0", "neo4j"],
            },
            required_sections=("artifact", "adr"),
            ontology_axioms=(
                OntologyAxiomCheckRule(
                    axiom_key="ax-no-sqlite",
                    forbidden_term="sqlite://",
                ),
            ),
        ),
        raise_on_failure=False,
    )
    assert drift_eval.status == "FAIL"
    assert drift_eval.schema_validation_passed is False
    assert "adr" in drift_eval.missing_sections
    assert drift_eval.ontology_axioms_passed is False
    assert drift_eval.pattern_drift_passed is False
    rule_ids = {f.rule_id for f in drift_eval.pattern_drift_findings}
    assert "DRIFT-UNAPPROVED-DEPENDENCY" in rule_ids
    assert "DRIFT-NO-SQLITE-IN-INTEGRATION" in rule_ids

    with pytest.raises(PatternDriftDetectedError) as exc_info:
        svc.evaluate_deterministic_gate(
            DeterministicGateInput(
                workspace_id=WORKSPACE_ID,
                run_id=RUN_ID,
                step_execution_id=STEP_EXEC_ID,
                step_key="validate-drift-raise",
                artifact_payload={
                    "artifact": "Utilisation non autorisée de celery",
                    "dependencies": ["celery"],
                },
            ),
            raise_on_failure=True,
        )
    assert exc_info.value.error_code == "ERR_PATTERN_DRIFT_DETECTED"


def test_story_4_1_sandbox_isolation_network_fs_memory_and_timeout_taxonomy() -> None:
    """Verify out-of-process sandbox isolation jails and `orcia_kernel.errors` taxonomy."""
    svc = DeterministicGateService()

    # 1. Network escape attempt -> exit_code 126 -> PolicyDeniedError (non-retryable)
    with pytest.raises(PolicyDeniedError) as net_exc:
        svc.evaluate_deterministic_gate(
            DeterministicGateInput(
                workspace_id=WORKSPACE_ID,
                run_id=RUN_ID,
                step_execution_id=STEP_EXEC_ID,
                step_key="step-net-escape",
                artifact_payload={"artifact": "test"},
                simulate_network_escape=True,
            ),
            raise_on_failure=True,
        )
    assert net_exc.value.error_code == "ERR_POLICY_DENIED"
    assert "ERR_SANDBOX_NETWORK_FORBIDDEN" in str(net_exc.value)

    # 2. Filesystem write outside ephemeral /tmp -> exit_code 126 -> PolicyDeniedError
    with pytest.raises(PolicyDeniedError) as fs_exc:
        svc.evaluate_deterministic_gate(
            DeterministicGateInput(
                workspace_id=WORKSPACE_ID,
                run_id=RUN_ID,
                step_execution_id=STEP_EXEC_ID,
                step_key="step-fs-escape",
                artifact_payload={"artifact": "test"},
                simulate_fs_escape_path="/var/tmp/orcia-forbidden-escape.txt",
            ),
            raise_on_failure=True,
        )
    assert "ERR_SANDBOX_FS_READONLY" in str(fs_exc.value)

    # 3. Ephemeral /tmp > 64 MB quota overflow -> exit_code 126 -> PolicyDeniedError
    with pytest.raises(PolicyDeniedError) as tmp_exc:
        svc.evaluate_deterministic_gate(
            DeterministicGateInput(
                workspace_id=WORKSPACE_ID,
                run_id=RUN_ID,
                step_execution_id=STEP_EXEC_ID,
                step_key="step-tmp-overflow",
                artifact_payload={"artifact": "test"},
                simulate_tmp_overflow_mb=65,
            ),
            raise_on_failure=True,
        )
    assert "ERR_SANDBOX_TMP_QUOTA_EXCEEDED" in str(tmp_exc.value)

    # 4. Memory ceiling > 256 MB -> exit_code 137 -> PolicyDeniedError
    with pytest.raises(PolicyDeniedError) as mem_exc:
        svc.evaluate_deterministic_gate(
            DeterministicGateInput(
                workspace_id=WORKSPACE_ID,
                run_id=RUN_ID,
                step_execution_id=STEP_EXEC_ID,
                step_key="step-mem-overflow",
                artifact_payload={"artifact": "test"},
                max_memory_mb=256,
                simulate_memory_alloc_mb=300,
            ),
            raise_on_failure=True,
        )
    assert "ERR_SANDBOX_MEMORY_LIMIT_EXCEEDED" in str(mem_exc.value)

    # 5. Hardware timeout exceeded -> exit_code 124 -> UpstreamTimeoutError (retryable)
    with pytest.raises(UpstreamTimeoutError) as timeout_exc:
        svc.evaluate_deterministic_gate(
            DeterministicGateInput(
                workspace_id=WORKSPACE_ID,
                run_id=RUN_ID,
                step_execution_id=STEP_EXEC_ID,
                step_key="step-timeout",
                artifact_payload={"artifact": "test"},
                timeout_ms=80,
                simulate_timeout_sleep_ms=400,
            ),
            raise_on_failure=True,
        )
    assert timeout_exc.value.error_code == "ERR_UPSTREAM_TIMEOUT"


def test_story_4_1_init_existing_project_and_init_skill_api_and_skill_executor() -> None:
    """Verify `init-existing-project`, `init-skill`, REST API endpoints, and `SkillStepExecutor`."""
    app = create_app()
    client = TestClient(app)

    # 1. Execute init-existing-project (Brownfield scan -> signed [ADOPTED] ARCHITECTURE-SPINE.md)
    proj_res = client.post(
        "/api/v1/bootstrap/init-existing-project?persona_key=marc",
        json={
            "workspace_id": WORKSPACE_ID,
            "repository_uri": "git://github.com/orcia/claims-service@main",
            "detected_dependencies": ["fastapi", "pydantic", "sqlalchemy", "httpx"],
            "architecture_paradigm": "Hexagonal Modular Monolith",
            "human_anchor_justification": (
                "Adoption formelle de la baseline architecturale Brownfield pour claims-service."
            ),
            "human_anchor_signature": "sig-marc-spine-v1",
            "spine_version": "1.0.0",
        },
    )
    assert proj_res.status_code == 200, proj_res.text
    proj_body = proj_res.json()
    assert proj_body["spine_baseline"]["status"] == "ADOPTED"
    assert "fastapi" in proj_body["spine_baseline"]["allowed_dependencies"]
    assert proj_body["run"]["workflow_uri"] == "orcia://system/bootstrap/init-existing-project"

    # 2. Evaluate deterministic gate via API against the newly adopted workspace Spine baseline
    eval_res = client.post(
        "/api/v1/gates/deterministic/evaluate?persona_key=marc",
        json={
            "workspace_id": WORKSPACE_ID,
            "run_id": RUN_ID,
            "step_execution_id": STEP_EXEC_ID,
            "step_key": "step-check-spine",
            "artifact_payload": {
                "artifact": "Service conforme à la baseline adoptée",
                "dependencies": ["fastapi", "httpx"],
            },
        },
    )
    assert eval_res.status_code == 200, eval_res.text
    assert eval_res.json()["evaluation"]["status"] == "PASS"

    # 3. Execute init-skill: valid skill passes Tier 1 Sandbox certification
    skill_ok = client.post(
        "/api/v1/bootstrap/init-skill?persona_key=marc",
        json={
            "workspace_id": WORKSPACE_ID,
            "skill_key": "json-schema-validator",
            "skill_uri": "orcia://skills/json-schema-validator",
            "title": "Validateur JSON Schema Déterministe",
            "description": "Valide les contrats JSON/YAML en Sandbox Palier 1.",
            "test_payload": {"artifact": "Self-test payload OK"},
        },
    )
    assert skill_ok.status_code == 200, skill_ok.text
    assert skill_ok.json()["gate_evaluation"]["status"] == "PASS"
    assert skill_ok.json()["catalog_item"]["resource_type"] == "skill"

    # 4. Execute init-skill: skill attempting network escape is rejected with HTTP 403
    skill_bad = client.post(
        "/api/v1/bootstrap/init-skill?persona_key=marc",
        json={
            "workspace_id": WORKSPACE_ID,
            "skill_key": "exfiltrator-skill",
            "skill_uri": "orcia://skills/exfiltrator-skill",
            "title": "Skill Malveillant",
            "description": "Tente d'ouvrir une socket réseau.",
            "simulate_network_escape": True,
        },
    )
    assert skill_bad.status_code == 403
    assert skill_bad.json()["error_code"] == "ERR_POLICY_DENIED"

    # 5. List gate evaluations via GET /api/v1/gates/evaluations
    list_res = client.get(
        f"/api/v1/gates/evaluations?run_id={RUN_ID}&persona_key=marc"
    )
    assert list_res.status_code == 200
    assert len(list_res.json()["evaluations"]) >= 1

    # 6. SkillStepExecutor (`orcia.step_executors`) invokes Tier 1 Sandbox for Deterministic Gate
    skill_exec = SkillStepExecutor()
    step_res = skill_exec.execute_step(
        StepExecutorContext(
            run_id=RUN_ID,
            root_run_id=RUN_ID,
            workspace_id=WORKSPACE_ID,
            workflow_uri="orcia://workflows/claims-engineering-delivery",
            step_key="gate-deterministic-step",
            step_title="Gate Déterministe",
            step_type="SKILL",
            execution_regime="INTERACTIVE_COACHING",
            directive="Vérifier la conformité Spine",
            declared_input_uris=(),
            resolved_inputs={"artifact": "Architecture conforme"},
            skill_uri="orcia://gates/deterministic/spine-check",
            metadata={"sandbox_tier": "TIER_1_WASM"},
        )
    )
    assert step_res.status == "EXECUTED"
    assert step_res.artifact_payload["gate_status"] == "PASS"

    with pytest.raises(DeterministicGateFailedError):
        skill_exec.execute_step(
            StepExecutorContext(
                run_id=RUN_ID,
                root_run_id=RUN_ID,
                workspace_id=WORKSPACE_ID,
                workflow_uri="orcia://workflows/claims-engineering-delivery",
                step_key="gate-fail-step",
                step_title="Gate Échec Schéma",
                step_type="SKILL",
                execution_regime="INTERACTIVE_COACHING",
                directive="",
                declared_input_uris=(),
                resolved_inputs={},
                skill_uri="orcia://gates/deterministic/schema-check",
                metadata={"sandbox_tier": "TIER_1_WASM", "required_sections": ["missing_sec"]},
            )
        )
