"""Unit & API tests for Story 11.4 (`packages/orcia-pack-builder` Processes 1 to 4)."""

from __future__ import annotations

from importlib.metadata import entry_points
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from orcia_api.main import create_app
from orcia_core.orchestration.errors import (
    HumanAnchorRequiredError,
    ObserverModeReadOnlyError,
)
from orcia_core.orchestration.pack_builder_processes import (
    DnaChainPackSeedSpec,
    PackBuilderSystemService,
    PackBuilderValidationError,
)
from orcia_pack_builder import (
    PACK_BUILDER_AGENTS,
    PACK_BUILDER_PROCESSES,
    get_pack_builder_manifest,
)

SAMPLE_STARLARK_SOLVENCY = """
def evaluate(ctx):
    data = orcia_sys.input("SolvencyPayloadV1")
    ratio = data.get("scr_ratio", 0)
    orcia_sys.assert_rule(
        rule_id="NORM-FIN-001",
        condition=(ratio >= 100),
        message="Le ratio SCR Solvabilité II doit être >= 100%.",
        evidence_ref="scr_ratio"
    )
"""


def test_pack_builder_entry_points_and_manifest() -> None:
    """Verify `orcia.packs` entry_point and the 4 agents + 5 governed processes."""
    eps = entry_points(group="orcia.packs")
    names = [ep.name for ep in eps]
    assert "pack_builder" in names

    manifest = get_pack_builder_manifest()
    assert manifest["pack_slug"] == "pack-builder"
    assert len(PACK_BUILDER_AGENTS) == 4
    assert len(PACK_BUILDER_PROCESSES) == 5
    handles = [a.handle for a in PACK_BUILDER_AGENTS]
    assert "@Architecte-Métier-Pack" in handles
    assert "@Rédacteur-Documentation-Orcia" in handles


@pytest.mark.asyncio
async def test_process1_create_business_pack_enforces_violet_anchor_and_ad20(
    tmp_path: Path,
) -> None:
    """Process 1 requires Violet Anchor (>= 30 chars), certifies Starlark, 0 writes to core."""
    svc = PackBuilderSystemService()

    # Reject READ_ONLY_OBSERVER
    with pytest.raises(ObserverModeReadOnlyError):
        await svc.create_business_pack(
            pack_slug="finance-solvency",
            title="Pack Finance Solvabilité II",
            version="0.1.0",
            domain_name="FINANCE",
            human_anchor_intent=(
                "Intention suffisamment longue pour passer la validation de longueur."
            ),
            dna_seeds=[],
            human_profiles=[],
            agents=[],
            workflows=[],
            actor_role="READ_ONLY_OBSERVER",
        )

    # Reject short/empty human anchor (< 30 chars)
    with pytest.raises(HumanAnchorRequiredError):
        await svc.create_business_pack(
            pack_slug="finance-solvency",
            title="Pack Finance Solvabilité II",
            version="0.1.0",
            domain_name="FINANCE",
            human_anchor_intent="Trop court",
            dna_seeds=[],
            human_profiles=[],
            agents=[],
            workflows=[],
        )

    # Reject reserved core/kernel pack_slug (AD-20)
    with pytest.raises(PackBuilderValidationError) as exc_info:
        await svc.create_business_pack(
            pack_slug="kernel",
            title="Pack Interdit",
            version="0.1.0",
            domain_name="CORE",
            human_anchor_intent="Intention métier longue mais ciblant un slug réservé au noyau.",
            dna_seeds=[],
            human_profiles=[],
            agents=[],
            workflows=[],
        )
    assert exc_info.value.error_code == "ERR_PACK_SLUG_RESERVED_OR_INVALID"

    # Valid Process 1 execution writing into tmp_path
    res = await svc.create_business_pack(
        pack_slug="finance-solvency",
        title="Pack Finance Solvabilité II",
        version="0.1.0",
        domain_name="FINANCE",
        human_anchor_intent=(
            "Garantir la conformité Solvabilité II pilier 1 et 3 sur tous les calculs actuariels."
        ),
        dna_seeds=[
            DnaChainPackSeedSpec(
                directive_code="DIR-SOLV2-01",
                directive_title="Directive Solvabilité II Pilier 1",
                norm_code="NORM-FIN-001",
                norm_title="Couverture SCR minimale à 100%",
                mechanism_code="MECH-SCR-100",
                rule_id="NORM-FIN-001",
                starlark_source=SAMPLE_STARLARK_SOLVENCY,
                passing_test_payload={"scr_ratio": 135},
                failing_test_payload={"scr_ratio": 82},
            )
        ],
        human_profiles=["Actuaire Senior", "Contrôleur des Risques"],
        agents=["@Actuaire-Vérificateur"],
        workflows=["solvency/compute-scr"],
        output_root_dir=tmp_path,
    )

    assert res.pack_id == "orcia://packs/orcia-pack-finance-solvency"
    assert res.kernel_or_core_touched is False
    assert res.starlark_rules_certified_count == 1
    assert res.max_starlark_elapsed_ms < 25.0
    assert (tmp_path / "packages/orcia-pack-finance-solvency/pack.yaml").exists()
    assert (tmp_path / "packages/orcia-pack-finance-solvency/rules/mech-scr-100.star").exists()


@pytest.mark.asyncio
async def test_process2_3_4_what_if_certify_and_workspace_export() -> None:
    """Verify Process 2 (What-If), Process 3 (Tier 1b & Tier 2), and Process 4 (scrubbing)."""
    svc = PackBuilderSystemService()

    # Process 2: What-If simulation preserving active run-lock.json
    what_if = await svc.evolve_business_pack_what_if(
        pack_slug="finance-solvency",
        previous_version="0.1.0",
        target_version="0.2.0",
        modified_norms=["NORM-FIN-001"],
        modified_workflows=["solvency/compute-scr"],
        subscribed_workspaces=[
            {
                "workspace_key": "actuariat-vie-ws",
                "workflows": ["solvency/compute-scr"],
                "active_runs_count": 2,
            }
        ],
        active_run_lock_ids=["run-lock-001", "run-lock-002"],
    )
    assert what_if.impacted_workspaces_count == 1
    assert what_if.active_run_locks_preserved is True
    assert what_if.untouched_run_lock_ids == ("run-lock-001", "run-lock-002")

    # Process 3: Tier 2 Container certification
    sample_digest = f"sha256:{'a' * 64}"
    cert_t2 = await svc.certify_pack_tool(
        tool_slug="actuarial-monte-carlo-cli",
        sandbox_tier="TIER_2_CONTAINER",
        container_image_digest=sample_digest,
        container_command=["pytest", "-q"],
    )
    assert cert_t2.certified is True
    assert cert_t2.network_isolated is True

    # Process 4: Export from workspace to pack with scrubbing
    promo = await svc.export_from_workspace_to_pack(
        source_workspace_key="actuariat-vie-ws",
        target_pack_slug="finance-solvency",
        target_pack_version="0.2.0",
        asset_kind="STARLARK_MECHANISM",
        asset_slug="scr-check",
        raw_asset_payload={
            "workspace_id": "actuariat-vie-ws",
            "artifact_path": "local://workspaces/actuariat-vie-ws/reports/scr.md",
            "vault_cred": "secret://vault/actuariat-vie-ws/token",  # pragma: allowlist secret
            "api_token": "pat_mcp_AbCdEf1234567890",  # pragma: allowlist secret
            "rule_id": "NORM-FIN-001",
        },
    )
    assert promo.scrubbed_references_count >= 4
    assert "workspace_id" not in promo.sanitized_payload
    assert "local://" not in str(promo.sanitized_payload)
    assert "pat_mcp_" not in str(promo.sanitized_payload)


@pytest.mark.asyncio
async def test_pack_builder_fastapi_endpoints() -> None:
    """Verify FastAPI endpoints for Story 11.4."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        manifest_resp = await client.get("/api/v1/pack-builder/manifest")
        assert manifest_resp.status_code == 200
        assert len(manifest_resp.json()["agents"]) == 4

        installed_before = await client.get("/api/v1/pack-builder/installed-packs")
        assert installed_before.status_code == 200
        before_keys = [p["pack_key"] for p in installed_before.json()["packs"]]
        assert "orcia-pack-sdlc" in before_keys
        assert "orcia-pack-builder" in before_keys

        create_resp = await client.post(
            "/api/v1/pack-builder/processes/create-pack",
            json={
                "pack_slug": "legal-contracts",
                "title": "Pack Juridique Contrats",
                "version": "0.1.0",
                "domain_name": "LEGAL",
                "human_anchor_intent": (
                    "Garantir la revue systématique des clauses de responsabilité et RGPD."
                ),
                "dna_seeds": [
                    {
                        "directive_code": "DIR-LEGAL-01",
                        "directive_title": "Plafond de responsabilité",
                        "norm_code": "NORM-FIN-001",
                        "norm_title": "Ratio couverture",
                        "mechanism_code": "MECH-LEGAL-01",
                        "rule_id": "NORM-FIN-001",
                        "starlark_source": SAMPLE_STARLARK_SOLVENCY,
                        "passing_test_payload": {"scr_ratio": 120},
                        "failing_test_payload": {"scr_ratio": 50},
                    }
                ],
                "human_profiles": ["Juriste Contrats"],
                "agents": ["@Analyste-Clauses"],
                "workflows": ["legal/review-nda"],
            },
        )
        assert create_resp.status_code == 201
        assert create_resp.json()["kernel_or_core_touched"] is False

        installed_after = await client.get("/api/v1/pack-builder/installed-packs")
        assert installed_after.status_code == 200
        after_keys = [p["pack_key"] for p in installed_after.json()["packs"]]
        assert "orcia-pack-legal-contracts" in after_keys
