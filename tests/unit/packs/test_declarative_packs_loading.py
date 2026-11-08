"""Unit tests for TASK-03 (`tests/unit/packs/test_declarative_packs_loading.py`).

Validates:
- `DeclarativePackLoader` hot-loads `packs/sdlc/` and `packs/orcia-docs/` and validates 100%
  of Pydantic schemas (`DeclarativePackManifest`, `ValueStreamMapSpec`, `WorkflowDefinitionV2`).
- Golden Rule #1: `packages/orcia-pack-sdlc/`, `packages/orcia-pack-builder/`, and
  `packages/orcia-kernel/` are permanently deleted; only `orcia-core` and `orcia-connectors`
  remain as backend Python packages under `packages/`.
- Golden Rule #2: `packs/` contains zero `.py`, `.ts`, or `.tsx` code files.
- Golden Rule #4: `vsm-mon-compte-idea-to-prod.yaml` contains the 11 steps, 4 phases, passage
  nodes, return loops, and opportunities `P1`, `P2`, `P3`, linked to the 4 unit workflows.
"""

from __future__ import annotations

from pathlib import Path

from orcia_core.packs.loader import DeclarativePackLoader, PackExporter
from orcia_core.workflows.schemas_v2 import ExecutionMode

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKS_ROOT = REPO_ROOT / "packs"
PACKAGES_ROOT = REPO_ROOT / "packages"


def test_only_two_python_packages_remain_and_legacy_packs_deleted() -> None:
    """Verify Golden Rule #1: only `orcia-core` and `orcia-connectors` in `packages/`."""
    assert not (PACKAGES_ROOT / "orcia-pack-sdlc").exists()
    assert not (PACKAGES_ROOT / "orcia-pack-builder").exists()
    assert not (PACKAGES_ROOT / "orcia-kernel").exists()

    python_packages = sorted(
        p.name for p in PACKAGES_ROOT.iterdir() if p.is_dir() and (p / "pyproject.toml").exists()
    )
    assert python_packages == ["orcia-connectors", "orcia-core"]


def test_declarative_packs_contain_zero_code_files() -> None:
    """Verify Golden Rule #2: `packs/<domain>/` contains zero Python or TypeScript/React code."""
    forbidden_suffixes = {".py", ".ts", ".tsx", ".js", ".jsx"}
    code_files = [
        p for p in PACKS_ROOT.rglob("*") if p.is_file() and p.suffix.lower() in forbidden_suffixes
    ]
    assert code_files == [], f"Unexpected code files in declarative packs/: {code_files}"


def test_declarative_pack_loader_loads_sdlc_and_orcia_docs() -> None:
    """Verify `DeclarativePackLoader` loads `packs/sdlc/` and `packs/orcia-docs/` cleanly."""
    loader = DeclarativePackLoader(PACKS_ROOT)
    bundles = loader.load_all_packs()

    assert "orcia-pack-sdlc" in bundles
    assert "orcia-pack-docs" in bundles

    sdlc = bundles["orcia-pack-sdlc"]
    assert sdlc.manifest.slug == "sdlc"
    assert len(sdlc.manifest.required_connectors) == 3
    connector_types = {c.connector_type for c in sdlc.manifest.required_connectors}
    assert connector_types == {
        "mcp:atlassian-jira",
        "mcp:atlassian-confluence",
        "mcp:git-provider",
    }
    assert set(sdlc.agents_markdown.keys()) == {
        "agent-us",
        "crl-etude-archi",
        "crl-socle-generateur",
        "orchestrateur-produit",
    }
    assert set(sdlc.skills_markdown.keys()) == {
        "decoupe-us-invest",
        "diagrammes-mermaid",
        "qualification-besoin",
        "redaction-prd-wsjf",
    }
    assert len(sdlc.gates_specs) == 6

    # Verify VSM (11 steps, 4 phases, human passage nodes, return loops, P1..P3)
    assert len(sdlc.vsm_specs) == 1
    vsm = sdlc.vsm_specs[0]
    assert vsm.id == "vsm-mon-compte-idea-to-prod"
    assert len(vsm.phases) == 4
    assert set(vsm.opportunities.keys()) == {"P1", "P2", "P3"}

    step_nodes = [n for n in vsm.nodes if n.node_type == "step"]
    passage_nodes = [n for n in vsm.nodes if n.node_type == "passage"]
    assert len(step_nodes) == 11
    assert len(passage_nodes) >= 5
    total_return_loops = sum(len(p.return_loops) for p in passage_nodes)
    assert total_return_loops >= 8

    # Verify the 4 bounded unit workflows
    wf_by_slug = {w.slug: w for w in sdlc.workflows}
    assert set(wf_by_slug.keys()) == {
        "wf-01-qualification-prd",
        "wf-03-etude-architecture",
        "wf-06-decoupe-us",
        "wf-08-dev-external-gate",
    }
    assert len(wf_by_slug["wf-01-qualification-prd"].sub_steps) == 3
    assert len(wf_by_slug["wf-03-etude-architecture"].sub_steps) == 4
    assert len(wf_by_slug["wf-06-decoupe-us"].sub_steps) == 5
    assert (
        wf_by_slug["wf-08-dev-external-gate"].execution_mode
        == ExecutionMode.EXTERNAL_DELEGATED_GATE
    )

    # Verify orcia-docs pack and zip export
    docs = bundles["orcia-pack-docs"]
    assert "redacteur-documentation-orcia" in docs.agents_markdown
    assert len(docs.workflows) == 1
    exported_zip = PackExporter.export_bundle_to_zip_bytes(sdlc, workspace_id="ws-mon-compte")
    assert len(exported_zip) > 1000
