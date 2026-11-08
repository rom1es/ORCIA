"""Unit tests for TASK-02 (`test_core_domain_isolation.py`).

Validates:
- Zero SDLC domain leak (`jira`, `confluence`, `git_branch`, `prd`, `wsjf`, `rovo`, `copilot`,
  `safe`) in `orcia-core` schemas, workflows, packs, storage, kernel, gates, and orchestration.
- `fork_workflow_as_draft` creates an immutable `vX.Y.Z-draft` fork when editing a `PUBLISHED`
  workflow (`CA-9.1.2`).
- `ClaimCheckStorageService` persists payloads `> 4 KB` via `ClaimCheckPointer` and verifies
  `SHA-256` integrity (`CA-9.1.3`).
- `DeclarativePackLoader` and `PackExporter` load and export 100% declarative packs.
"""

from __future__ import annotations

import ast
import io
import re
import zipfile
from pathlib import Path

from orcia_core.packs.loader import (
    DeclarativePackLoader,
    DeclarativePackManifest,
    LoadedPackBundle,
    PackExporter,
    QuickActionSpec,
    RequiredConnectorSpec,
)
from orcia_core.storage.claim_check import (
    CLAIM_CHECK_INLINE_THRESHOLD_BYTES,
    ClaimCheckStorageService,
)
from orcia_core.workflows.schemas_v2 import (
    DeterministicSubStepSpec,
    StepControlsPipeline,
    ValueStreamMapSpec,
    VsmStepNodeSpec,
    WorkflowDefinitionV2,
    WorkflowLifecycleStatus,
    fork_workflow_as_draft,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
ORCIA_CORE_SRC = REPO_ROOT / "packages" / "orcia-core" / "src" / "orcia_core"


def test_core_domain_isolation_ast_and_regex() -> None:
    """Verify zero SDLC domain leak in `orcia-core` (`CA-9.1.1`)."""
    # 1. Across all of packages/orcia-core: zero occurrences of git_branch, wsjf, rovo, copilot, prd
    strict_global_pattern = re.compile(
        r"\b(git_branch|wsjf|rovo|copilot|prd)\b",
        re.IGNORECASE,
    )
    for py_file in sorted(ORCIA_CORE_SRC.rglob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                assert not strict_global_pattern.search(node.name), (
                    f"Forbidden SDLC identifier {node.name!r} in {py_file}"
                )
        match = strict_global_pattern.search(source)
        assert match is None, f"Forbidden SDLC keyword {match.group(0)!r} found in {py_file}"

    # 2. Across workflows, packs, storage, kernel, orchestration, and gates:
    # zero occurrences of jira, confluence, git_branch, wsjf, rovo, copilot, safe, prd
    isolated_packages = (
        ORCIA_CORE_SRC / "workflows",
        ORCIA_CORE_SRC / "packs",
        ORCIA_CORE_SRC / "storage",
        ORCIA_CORE_SRC / "kernel",
        ORCIA_CORE_SRC / "orchestration",
        ORCIA_CORE_SRC / "gates",
    )
    isolated_pattern = re.compile(
        r"\b(jira|confluence|git_branch|wsjf|rovo|copilot|safe|prd)\b",
        re.IGNORECASE,
    )
    for folder in isolated_packages:
        for py_file in sorted(folder.rglob("*.py")):
            source = py_file.read_text(encoding="utf-8")
            match = isolated_pattern.search(source)
            assert match is None, f"Forbidden domain keyword {match.group(0)!r} found in {py_file}"


def test_claim_check_storage_above_4kb_and_sha256_verification() -> None:
    """Verify artifacts > 4 KB are stored in S3 with SHA-256 ClaimCheckPointer (`CA-9.1.3`)."""
    storage = ClaimCheckStorageService()
    large_markdown = "# Dossier d'Architecture\n\n" + ("Ligne de spécification détaillée.\n" * 200)
    raw_bytes = large_markdown.encode("utf-8")
    assert len(raw_bytes) > CLAIM_CHECK_INLINE_THRESHOLD_BYTES

    pointer = storage.store_artifact(
        run_id="run-001",
        step_id="step-03-da",
        iteration=1,
        content=raw_bytes,
        mime_type="text/markdown",
    )
    assert pointer.s3_uri.startswith("s3://orcia-artifacts/run-001/step-03-da/iter-1/")
    assert pointer.byte_size == len(raw_bytes)
    assert len(pointer.sha256) == 64

    loaded_text = storage.resolve_artifact_text(pointer)
    assert loaded_text == large_markdown


def test_fork_published_workflow_creates_draft_version() -> None:
    """Verify editing a PUBLISHED workflow creates an immutable `vX.Y.Z-draft` fork (`CA-9.1.2`)."""
    published_wf = WorkflowDefinitionV2(
        id="wf-01-qualif",
        pack_id="pack-sample",
        slug="wf-01-qualification",
        title="Workflow Qualification",
        version="1.0.0",
        status=WorkflowLifecycleStatus.PUBLISHED,
        sub_steps=[
            DeterministicSubStepSpec(
                id="sub-01",
                name="Qualification",
                short_label="Qualif",
                trigger_condition_label="Démarrage",
                role_description="Qualifier la demande",
                instruction_prompt_or_ref="pack://sample/agents/orchestrateur",
                output_description="Note de qualification",
                checkpoint_label="Valider la qualification",
            )
        ],
        controls=StepControlsPipeline(),
    )

    draft_wf = fork_workflow_as_draft(published_wf)
    assert published_wf.status == WorkflowLifecycleStatus.PUBLISHED
    assert published_wf.version == "1.0.0"
    assert draft_wf.status == WorkflowLifecycleStatus.DRAFT
    assert draft_wf.version.endswith("-draft")


def test_declarative_pack_loader_and_zip_exporter(tmp_path: Path) -> None:
    """Verify `DeclarativePackLoader` and `PackExporter` round-trip a declarative pack."""
    manifest = DeclarativePackManifest(
        id="pack-sample-domain",
        slug="sample-domain",
        name="Pack Sample Domain",
        version="1.0.0",
        description="Pack de test déclaratif",
        rbac_namespace="sample",
        required_connectors=[
            RequiredConnectorSpec(
                connector_type="mcp:sql-readonly",
                required_scopes=["read"],
                used_for="Lecture analytique",
            )
        ],
        quick_actions=[
            QuickActionSpec(
                id="qa-run",
                label="Lancer qualification",
                target_workflow_slug="wf-01-sample",
            )
        ],
    )
    vsm = ValueStreamMapSpec(
        id="vsm-sample",
        pack_id="pack-sample-domain",
        slug="sample-idea-to-prod",
        title="Chaîne de Valeur Sample",
        subtitle="Sous-titre VSM",
        source_note="Note de source",
        guiding_principle="Principe directeur",
        phases=[{"id": "p1", "num": "01", "label": "Cadrage", "color_token": "blue"}],
        nodes=[
            VsmStepNodeSpec(
                num="01",
                phase_id="p1",
                title="Étape 1",
                linked_workflow_id="wf-01-sample",
                input_actuel="Entrée actuelle",
                input_ia="Entrée IA",
                output_actuel="Sortie actuelle",
                output_ia="Sortie IA",
                actor_actuel="Humain",
                actor_ia="Agent + Humain",
                validation_actuel="Validation manuelle",
                validation_ia="Validation assistée",
            )
        ],
    )
    wf = WorkflowDefinitionV2(
        id="wf-01-sample",
        pack_id="pack-sample-domain",
        slug="wf-01-sample",
        title="Workflow Sample",
        version="1.0.0",
        status=WorkflowLifecycleStatus.PUBLISHED,
        sub_steps=[
            DeterministicSubStepSpec(
                id="sub-1",
                name="Sous-étape 1",
                short_label="Sub 1",
                trigger_condition_label="Démarrage",
                role_description="Analyser le dossier",
                instruction_prompt_or_ref="pack://sample-domain/agents/analyst",
                output_description="Synthèse",
                checkpoint_label="Valider la synthèse",
            )
        ],
    )

    bundle = LoadedPackBundle(
        manifest=manifest,
        bundle_sha256="0" * 64,
        glossary={"terms": [{"key": "dossier", "label": "Dossier Client"}]},
        agents_markdown={"analyst": "# Agent Analyste\nMission : qualifier le dossier."},
        skills_markdown={"synthese": "# Skill Synthèse\nStructurer en 3 parties."},
        gates_specs={"det-contract": {"runner": "markdown_contract_runner"}},
        vsm_specs=[vsm],
        workflows=[wf],
    )

    zip_bytes = PackExporter.export_bundle_to_zip_bytes(bundle, workspace_id="ws-demo-01")
    extract_root = tmp_path / "extracted"
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        zf.extractall(extract_root)

    loader = DeclarativePackLoader(extract_root)
    loaded_packs = loader.load_all_packs()
    assert "pack-sample-domain" in loaded_packs
    loaded = loaded_packs["pack-sample-domain"]
    assert loaded.manifest.slug == "sample-domain"
    assert len(loaded.vsm_specs) == 1
    assert len(loaded.workflows) == 1
    assert "analyst" in loaded.agents_markdown
