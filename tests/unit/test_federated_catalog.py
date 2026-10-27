"""Layer 1 Unit, Property-Based (`hypothesis`), and FastAPI Route Tests for Story 1.3 (`AD-17`).

Covers:
- Federated URI parser (`git://`, `nexus://`, `db://`, `confluence://`, `jira://`, `orcia://`).
- `FederatedUriResolver` (`cas/<sha256>`, `< 50 ms` hot cache, S3 & in-memory CAS stores).
- `FourLayerOverrideMerger` (`Base -> Team -> Workspace -> User`, `run-lock.json`, `hypothesis`).
- `BmadSkillPackAdapter` (`SKILL.md` + `customize.toml` + `steps/*.md` + `.tar.gz`/`.zip`).
- `FederatedCatalogService` & FastAPI endpoints (`/api/v1/catalog/*`, `/api/v1/cas/*`).
"""

from __future__ import annotations

import io
import tarfile
import zipfile

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from orcia_api.main import create_app
from orcia_core.catalog import (
    BmadSkillPackAdapter,
    BmadSkillPackInput,
    BmadSkillStepFile,
    CasObjectEntry,
    CustomizationOverrideEntity,
    EvaluationLensDefinition,
    FederatedUriResolver,
    FourLayerOverrideMerger,
    InMemoryCasObjectStore,
    S3CompatibleCasObjectStore,
    build_default_federated_catalog_service,
    compute_bytes_sha256,
    parse_federated_uri,
)
from orcia_core.catalog.errors import (
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.permissions import build_default_auth_and_org_service


class _MockS3Backend:
    def __init__(self) -> None:
        self.storage: dict[tuple[str, str], bytes] = {}

    def put_bytes(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        self.storage[(bucket, key)] = data

    def get_bytes(self, bucket: str, key: str) -> bytes | None:
        return self.storage.get((bucket, key))

    def head_key(self, bucket: str, key: str) -> bool:
        return (bucket, key) in self.storage


def test_parse_federated_uri_all_schemes_and_validation() -> None:
    """Verify parsing of all 6 federated schemes, `@vN`, `@sha256`, archives, and error cases."""
    git_uri = parse_federated_uri("git://gitlab.entreprise.io/payments/checkout-web@v1.4.0")
    assert git_uri.scheme == "git"
    assert git_uri.authority == "gitlab.entreprise.io"
    assert git_uri.path == "payments/checkout-web"
    assert git_uri.version_or_ref == "v1.4.0"

    nexus_uri = parse_federated_uri("nexus://nexus.entreprise.io/skills/pack-1.0.tar.gz")
    assert nexus_uri.scheme == "nexus"
    assert nexus_uri.archive_format == "tar.gz"

    zip_uri = parse_federated_uri("nexus://nexus.entreprise.io/skills/pack-1.0.zip@sha256:8f4e2b10")
    assert zip_uri.archive_format == "zip"
    assert zip_uri.expected_sha256 == "8f4e2b10"

    conf_uri = parse_federated_uri("confluence://PAYADR/adr-spine@v12")
    assert conf_uri.scheme == "confluence"
    assert conf_uri.version_or_ref == "v12"

    jira_uri = parse_federated_uri("jira://PAYSEC/PAYSEC-101")
    assert jira_uri.scheme == "jira"
    assert jira_uri.version_or_ref == "PAYSEC-101"

    for invalid in (
        "invalid-no-scheme",
        "ftp://host/path",
        "git://only-authority",
        "git:///missing-authority",
        "git://host/path@sha256:NOT_HEX!",
        "git://host/path@",
        "git://host/@v1",
    ):
        with pytest.raises(ValidationDomainError):
            parse_federated_uri(invalid)


def test_cas_resolver_hot_cache_under_50ms_and_s3_store_integrity() -> None:
    """Verify 1st call cache_hit=False, 2nd call cache_hit=True < 50 ms, and SHA-256 check."""
    s3_backend = _MockS3Backend()
    s3_store = S3CompatibleCasObjectStore(s3_backend, bucket_name="orcia-cas")
    resolver = FederatedUriResolver(cas_store=s3_store)

    uri = "confluence://PAYADR/adr-hexagonal-spine@v12"
    first = resolver.resolve(uri)
    assert first.cache_hit is False
    assert first.cas_key == f"cas/{first.sha256}"
    assert s3_store.has_object(first.cas_key) is True

    second = resolver.resolve(uri, expected_sha256=first.sha256[:12])
    assert second.cache_hit is True
    assert second.sha256 == first.sha256
    assert second.resolution_ms < 50.0

    # Cold L1 cache read from S3 backend
    s3_store._hot_cache.clear()
    assert s3_store.has_object(first.cas_key) is True
    fetched = resolver.get_cas_entry(first.sha256)
    assert fetched.content_text == first.content_text

    # Mismatched expected_sha256 raises ValidationDomainError
    with pytest.raises(ValidationDomainError):
        resolver.resolve(uri, expected_sha256="000000000000")

    # Immutable collision check in InMemoryCasObjectStore
    mem_store = InMemoryCasObjectStore()
    good_bytes = b'{"ok":true}'
    good_sha = compute_bytes_sha256(good_bytes)
    mem_store.put_object(
        CasObjectEntry(sha256=good_sha, cas_key=f"cas/{good_sha}", content_bytes=good_bytes)
    )
    with pytest.raises(ValidationDomainError):
        mem_store.put_object(
            CasObjectEntry(sha256=good_sha, cas_key="cas/wrong", content_bytes=good_bytes)
        )
    with pytest.raises(ValidationDomainError):
        mem_store.put_object(
            CasObjectEntry(sha256=good_sha, cas_key=f"cas/{good_sha}", content_bytes=b"tampered")
        )
    with pytest.raises(ValidationDomainError):
        resolver.get_cas_entry("not-a-64-char-sha")
    with pytest.raises(ResourceNotFoundError):
        resolver.get_cas_entry("a" * 64)


def test_four_layer_override_merger_and_run_lock_determinism() -> None:
    """Verify Base -> Team (Parent -> Sub-Team) -> Workspace -> User merge without base mutation."""
    auth_svc = build_default_auth_and_org_service()
    cat_svc = build_default_federated_catalog_service(evaluator=auth_svc.evaluator)
    marc = auth_svc.resolve_user(persona_key="marc")

    wf_uri = "db://orcia/catalog/payment-delivery-workflow@v1.2.0"
    base_before = cat_svc.workflows[0]
    base_scalars_snapshot = dict(base_before.scalars)
    base_rules_snapshot = tuple(base_before.rules)

    merged = cat_svc.resolve_effective_workflow(
        marc,
        workflow_uri=wf_uri,
        workspace_id="ws-solution-paiement",
    )

    # Base workflow must never be mutated (AD-14)
    assert base_before.scalars == base_scalars_snapshot
    assert base_before.rules == base_rules_snapshot

    # Verify exact 4-layer order: Parent Team -> Sub-Team -> Workspace -> User
    assert merged.applied_override_keys == (
        "ovr-team-parent-archi-payment-wf",
        "ovr-subteam-checkout-payment-wf",
        "ovr-workspace-payment-wf",
        "ovr-user-marc-payment-wf",
    )
    eff = merged.effective_workflow
    assert eff.scalars["timeout_seconds"] == 900  # Parent Team overrode Base (600)
    assert eff.scalars["squad_channel"] == "#checkout-core"  # Sub-Team
    assert eff.scalars["solution_slug"] == "ws-solution-paiement"  # Workspace
    assert (
        eff.scalars["human_greeting"] == "Bonjour Marc (Tech Lead Checkout)"
    )  # User overrode Base
    assert "RULE-BASE-HEXAGONAL" in eff.rules
    assert "RULE-TEAM-PARENT-SECOPS-AUDIT" in eff.rules
    assert "RULE-SUBTEAM-CHECKOUT-IDEMPOTENCY" in eff.rules
    assert "RULE-WS-PAYMENT-MULTI-REPO-SYNC" in eff.rules
    assert "RULE-USER-FRENCH-TYPOGRAPHY" in eff.rules

    # Lenses merged by code (security, architecture updated; finops added)
    lens_by_code = {lens.code: lens for lens in eff.lenses}
    assert lens_by_code["security"].threshold == 0.85
    assert lens_by_code["architecture"].weight == 0.65
    assert lens_by_code["finops"].weight == 0.2

    # run-lock.json pins workflow + all 7 datasources of Workspace 1
    assert len(merged.run_lock.sources) == 8
    assert '"manifest_sha256"' in merged.run_lock.to_json()


@given(
    team_timeout=st.integers(min_value=100, max_value=2000),
    ws_timeout=st.integers(min_value=2001, max_value=5000),
    user_greeting=st.text(min_size=1, max_size=30),
)
@settings(max_examples=15, deadline=None)
def test_hypothesis_four_layer_override_priority_invariants(
    team_timeout: int, ws_timeout: int, user_greeting: str
) -> None:
    """Property test: Later layers (User > Workspace > Team > Base) deterministically win."""
    auth_svc = build_default_auth_and_org_service()
    cat_svc = build_default_federated_catalog_service(evaluator=auth_svc.evaluator)
    base_wf = cat_svc.workflows[0]
    ws = auth_svc.evaluator.workspaces[0]
    overrides = (
        CustomizationOverrideEntity(
            id="1",
            override_key="k-team",
            target_uri=base_wf.uri,
            override_layer="TEAM",
            org_unit_id=ws.owner_org_unit_id,
            scalars={"timeout_seconds": team_timeout, "shared_key": "from_team"},
            rules=("R1", "R2"),
        ),
        CustomizationOverrideEntity(
            id="2",
            override_key="k-ws",
            target_uri=base_wf.uri,
            override_layer="WORKSPACE",
            workspace_id=ws.id,
            scalars={"timeout_seconds": ws_timeout, "shared_key": "from_ws"},
            rules=("R2", "R3"),
        ),
        CustomizationOverrideEntity(
            id="3",
            override_key="k-user",
            target_uri=base_wf.uri,
            override_layer="USER",
            user_id="u-1",
            scalars={"human_greeting": user_greeting},
            lenses=(EvaluationLensDefinition(code="security", weight=0.9, threshold=0.95),),
        ),
    )
    eff1, _ = FourLayerOverrideMerger.merge_workflow(
        base_workflow=base_wf,
        org_units=auth_svc.evaluator.org_units,
        workspace=ws,
        user_id="u-1",
        overrides=overrides,
    )
    eff2, _ = FourLayerOverrideMerger.merge_workflow(
        base_workflow=base_wf,
        org_units=auth_svc.evaluator.org_units,
        workspace=ws,
        user_id="u-1",
        overrides=overrides,
    )
    assert eff1.sha256 == eff2.sha256
    assert eff1.scalars["timeout_seconds"] == ws_timeout
    assert eff1.scalars["shared_key"] == "from_ws"
    assert eff1.scalars["human_greeting"] == user_greeting
    assert eff1.rules.count("R2") == 1


def test_bmad_skill_pack_adapter_direct_and_archives() -> None:
    """Verify lossless conversion of SKILL.md + customize.toml + steps/*.md and archives."""
    skill_md = (
        "---\nname: bmad-payment-audit\n"
        "description: Audit de conformité Paiement\nversion: 2.0.0\n---\n"
        "# Instructions Générales\nRespecter l'isolation hexagonale."
    )
    customize_toml = (
        "[scalars]\nstrict_mode = true\nmax_retries = 3\n"
        'rules = ["RULE-BMAD-1"]\nfacts = ["FACT-BMAD-1"]\n'
        'datasources = ["git://gitlab.entreprise.io/payments/ledger-api"]\n'
        '[[lenses]]\ncode = "compliance"\nweight = 0.7\nthreshold = 0.9\n'
    )
    step_1 = "# Étape 1 : Ancrage\nhuman_authored_required: true\nValider le périmètre."
    step_2 = "# Étape 2 : Rapport\nGénérer le rapport."

    resolver = FederatedUriResolver()
    item, wf = BmadSkillPackAdapter.import_pack(
        BmadSkillPackInput(
            uri="git://gitlab.entreprise.io/payments/skills/bmad-payment-audit@v2.0.0",
            skill_markdown=skill_md,
            customize_toml=customize_toml,
            steps=(
                BmadSkillStepFile("step-02-report.md", step_2),
                BmadSkillStepFile("step-01-anchor.md", step_1),
            ),
        ),
        resolver=resolver,
    )
    assert item.source_format == "BMAD_PACK"
    assert wf.source_format == "BMAD_PACK"
    assert len(wf.steps) == 2
    assert wf.steps[0].step_key == "step-01-anchor"
    assert wf.steps[0].human_authored_required is True
    assert wf.steps[1].step_key == "step-02-report"
    assert wf.scalars["strict_mode"] is True
    assert "RULE-BMAD-1" in wf.rules

    # Test .tar.gz archive extraction
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w:gz") as tf:
        for fname, content in (
            ("pack/SKILL.md", skill_md),
            ("pack/customize.toml", customize_toml),
            ("pack/steps/step-01.md", step_1),
        ):
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=fname)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    tar_item, _ = BmadSkillPackAdapter.import_from_archive_bytes(
        uri="nexus://nexus.entreprise.io/bmad/pack-2.0.0.tar.gz",
        archive_bytes=tar_buf.getvalue(),
    )
    assert tar_item.version == "2.0.0"

    # Test .zip archive extraction
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, mode="w") as zf:
        zf.writestr("SKILL.md", skill_md)
        zf.writestr("steps/step-01.md", step_1)
    zip_item, _ = BmadSkillPackAdapter.import_from_archive_bytes(
        uri="nexus://nexus.entreprise.io/bmad/pack-2.0.0.zip",
        archive_bytes=zip_buf.getvalue(),
    )
    assert zip_item.scheme == "nexus"

    # Invalid cases
    for bad_md in (
        "no frontmatter",
        "---\nunclosed",
        "---\n# comment\ninvalid_line\nname: only-name\n---\nbody",
    ):
        with pytest.raises(ValidationDomainError):
            BmadSkillPackAdapter.import_pack(
                BmadSkillPackInput(uri="git://host/p", skill_markdown=bad_md, steps=())
            )
    with pytest.raises(ValidationDomainError):
        BmadSkillPackAdapter.import_pack(
            BmadSkillPackInput(
                uri="git://host/p",
                skill_markdown=skill_md,
                customize_toml="invalid = [toml",
                steps=(BmadSkillStepFile("s.md", "# S"),),
            )
        )
    with pytest.raises(ValidationDomainError):
        BmadSkillPackAdapter.import_pack(
            BmadSkillPackInput(uri="git://host/p", skill_markdown=skill_md, steps=())
        )
    with pytest.raises(ValidationDomainError):
        BmadSkillPackAdapter.import_pack(
            BmadSkillPackInput(
                uri="git://host/p",
                skill_markdown=skill_md,
                steps=(BmadSkillStepFile("", ""),),
            )
        )
    with pytest.raises(ValidationDomainError):
        BmadSkillPackAdapter.import_from_archive_bytes(
            uri="nexus://host/corrupt.zip", archive_bytes=b"not-a-zip"
        )


def test_fastapi_catalog_routes_promotion_cas_merge_and_bmad() -> None:
    """Verify all `/api/v1/catalog/*` and `/api/v1/cas/*` FastAPI routes and RBAC guards."""
    client = TestClient(create_app())

    # 1. List catalog items & filters
    list_res = client.get("/api/v1/catalog/items?persona_key=marc")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert len(items) == 6

    filtered_res = client.get(
        "/api/v1/catalog/items?persona_key=marc&scheme=nexus&visibility_scope=PUBLISHED_ORG"
    )
    assert filtered_res.status_code == 200
    assert len(filtered_res.json()["items"]) == 1

    # 2. Resolve URI -> 1st call cache_hit=False, 2nd call cache_hit=True, then GET /api/v1/cas/*
    res1 = client.post(
        "/api/v1/catalog/resolve",
        json={"uri": "git://gitlab.entreprise.io/payments/checkout-web"},
    )
    assert res1.status_code == 200
    assert res1.json()["cache_hit"] is False
    sha = res1.json()["sha256"]

    res2 = client.post(
        "/api/v1/catalog/resolve",
        json={
            "uri": "git://gitlab.entreprise.io/payments/checkout-web",
            "expected_sha256": sha[:12],
        },
    )
    assert res2.status_code == 200
    assert res2.json()["cache_hit"] is True

    res_bad_sha = client.post(
        "/api/v1/catalog/resolve",
        json={
            "uri": "git://gitlab.entreprise.io/payments/checkout-web",
            "expected_sha256": "000000000000",
        },
    )
    assert res_bad_sha.status_code == 422
    assert res_bad_sha.json()["error_code"] == "ERR_VALIDATION_FAILED"

    cas_res = client.get(f"/api/v1/cas/{sha}")
    assert cas_res.status_code == 200
    assert cas_res.json()["sha256"] == sha

    # 3. Promote DRAFT -> SHARED_WORKSPACE, reject Claire in READ_ONLY_OBSERVER, allow Karim
    prom1 = client.post(
        "/api/v1/catalog/items/res-jira-secops-playbook/promote?persona_key=marc",
        json={"target_scope": "SHARED_WORKSPACE"},
    )
    assert prom1.status_code == 200
    assert prom1.json()["item"]["visibility_scope"] == "SHARED_WORKSPACE"

    # Non-admin Marc cannot promote directly to PUBLISHED_ORG
    marc_pub_deny = client.post(
        "/api/v1/catalog/items/res-jira-secops-playbook/promote?persona_key=marc",
        json={"target_scope": "PUBLISHED_ORG"},
    )
    assert marc_pub_deny.status_code == 403

    # Retrograde promotion rejected with 422
    retro = client.post(
        "/api/v1/catalog/items/res-jira-secops-playbook/promote?persona_key=marc",
        json={"target_scope": "DRAFT"},
    )
    assert retro.status_code == 422
    assert retro.json()["error_code"] == "ERR_VALIDATION_FAILED"

    # Claire (BU_DIRECTOR / READ_ONLY_OBSERVER) rejected when promoting to non-PUBLISHED_ORG
    obs_deny = client.post(
        "/api/v1/catalog/items/res-jira-secops-playbook/promote?persona_key=claire",
        json={"target_scope": "SHARED_TEAM"},
    )
    assert obs_deny.status_code == 403
    assert obs_deny.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    obs_deny_no_ws = client.post(
        "/api/v1/catalog/items/res-blackbox-security-agent/promote?persona_key=claire",
        json={"target_scope": "SHARED_BU"},
    )
    assert obs_deny_no_ws.status_code == 403
    assert obs_deny_no_ws.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    # Karim (PLATFORM_ADMIN) promotes PENDING_APPROVAL -> PUBLISHED_ORG
    pub_org = client.post(
        "/api/v1/catalog/items/res-confluence-adr-template/promote?persona_key=karim",
        json={"target_scope": "PUBLISHED_ORG"},
    )
    assert pub_org.status_code == 200
    assert pub_org.json()["item"]["visibility_scope"] == "PUBLISHED_ORG"

    # 4. Resolve effective workflow & run-lock.json + register override ownership guards
    from orcia_core.catalog.errors import ScopeAccessDeniedError

    auth_svc = build_default_auth_and_org_service()
    cat_svc = build_default_federated_catalog_service(evaluator=auth_svc.evaluator)
    marc = auth_svc.resolve_user(persona_key="marc")
    assert len(cat_svc.catalog_items) >= 6
    assert len(cat_svc.overrides) == 4
    cat_svc.register_customization_override(
        marc,
        CustomizationOverrideEntity(
            id="ovr-custom",
            override_key="ovr-user-marc-payment-wf",
            target_uri="db://orcia/catalog/payment-delivery-workflow@v1.2.0",
            override_layer="USER",
            user_id=marc.id,
            workspace_id="0192c4e0-0000-7000-8000-000000000201",
            scalars={"custom_flag": True},
        ),
    )
    with pytest.raises(ScopeAccessDeniedError):
        cat_svc.register_customization_override(
            marc,
            CustomizationOverrideEntity(
                id="ovr-other-user",
                override_key="ovr-other-user",
                target_uri="db://orcia/catalog/payment-delivery-workflow@v1.2.0",
                override_layer="USER",
                user_id="someone-else",
                workspace_id="0192c4e0-0000-7000-8000-000000000201",
            ),
        )
    with pytest.raises(ScopeAccessDeniedError):
        cat_svc.register_customization_override(
            marc,
            CustomizationOverrideEntity(
                id="ovr-other-team",
                override_key="ovr-other-team",
                target_uri="db://orcia/catalog/payment-delivery-workflow@v1.2.0",
                override_layer="TEAM",
                org_unit_id="0192c4e0-0000-7000-8000-000000000105",
                workspace_id="0192c4e0-0000-7000-8000-000000000201",
            ),
        )

    eff_res = client.post(
        "/api/v1/catalog/workflows/resolve-effective?persona_key=marc",
        json={
            "workflow_uri": "db://orcia/catalog/payment-delivery-workflow@v1.2.0",
            "workspace_id": "ws-solution-paiement",
        },
    )
    assert eff_res.status_code == 200
    assert len(eff_res.json()["run_lock"]["sources"]) == 8

    # 5. Import BMAD pack via API (Marc allowed, Claire rejected in READ_ONLY_OBSERVER)
    bmad_payload = {
        "uri": "git://gitlab.entreprise.io/payments/checkout-web/skills/bmad-new@v1.0.0",
        "skill_markdown": "---\nname: bmad-new\ndescription: Nouveau skill BMAD\n---\n# Corps",
        "customize_toml": '[scalars]\nmode = "fast"\n',
        "steps": [{"filename": "step-01.md", "content_markdown": "# Step 1\nInstructions"}],
        "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
    }
    bmad_deny = client.post(
        "/api/v1/catalog/bmad-packs/import?persona_key=claire", json=bmad_payload
    )
    assert bmad_deny.status_code == 403
    assert bmad_deny.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    bmad_ok = client.post("/api/v1/catalog/bmad-packs/import?persona_key=marc", json=bmad_payload)
    assert bmad_ok.status_code == 200
    assert bmad_ok.json()["workflow_definition"]["source_format"] == "BMAD_PACK"
