"""Unit tests for Story 11.5 — Process 5 `generate-and-attach-help` & `validate_help_article`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from orcia_api.main import create_app
from orcia_core.orchestration.errors import ObserverModeReadOnlyError
from orcia_core.orchestration.help_generator_and_validator import (
    HelpArticleDeterministicValidator,
    HelpArticleValidationError,
    HelpGenerationAndHotAttachmentService,
)


class _FakeRedis:
    def __init__(self) -> None:
        self.deleted_keys: list[str] = []

    def delete(self, key: str) -> None:
        self.deleted_keys.append(key)


def test_validate_help_article_passes_valid_bilingual_markdown_under_5s() -> None:
    svc = HelpGenerationAndHotAttachmentService()
    md_fr, md_en = svc.render_bilingual_help_markdown(
        article_id="help.claims.triage",
        version="1.2.0",
        pack_id="orcia://packs/orcia-pack-claims",
        title_fr="Aide Triage Sinistres",
        title_en="Claims Triage Help",
        bound_routes=["/cockpit", "/mes-espaces/$id/glossary"],
        roles_allowed=["CONTRIBUTOR", "ARCHITECT"],
        glossary_terms=["Franchise Contractuelle", "Sinistre"],
        related_workflows=["claims/triage-flow"],
        purpose_fr="Explique le triage rapide des sinistres IARD.",
        purpose_en="Explains rapid P&C claims triage.",
        steps_fr=["Ouvrir le Cockpit", "Vérifier les pièces"],
        steps_en=["Open the Cockpit", "Check documents"],
        faq_fr=["Que faire si un justificatif manque ?"],
        faq_en=["What if a supporting document is missing?"],
        ui_component_name="ContextualHelpColumnAndCenter",
    )

    rep_fr = svc.validator.validate_help_article(
        markdown_text=md_fr,
        lang="fr",
        known_glossary_terms=["Franchise Contractuelle", "Sinistre"],
    )
    rep_en = svc.validator.validate_help_article(
        markdown_text=md_en,
        lang="en",
        known_glossary_terms=["Franchise Contractuelle", "Sinistre"],
    )

    assert rep_fr.passed is True
    assert rep_fr.bound_routes_valid is True
    assert rep_fr.ui_components_and_sections_valid is True
    assert rep_fr.glossary_and_zero_secret_valid is True
    assert rep_fr.elapsed_ms < 5000.0
    assert rep_en.passed is True
    assert rep_en.elapsed_ms < 5000.0


def test_validate_help_article_rejects_unknown_routes_components_sections_and_secrets() -> None:
    validator = HelpArticleDeterministicValidator()
    leaked_tok = "pat_" + "mcp_9876543210abcdef"
    bad_md = (
        "---\n"
        'id: "help.bad"\n'
        'version: "1.0.0"\n'
        'bound_routes: ["/non-existent-route-xyz"]\n'
        'glossary_terms: ["TermeInconnu"]\n'
        "---\n\n"
        "# Aide invalide\n"
        "Utilise `<NonExistentPhantomWidget />` avec jeton "
        f"{leaked_tok}.\n"
    )
    rep = validator.validate_help_article(
        markdown_text=bad_md,
        lang="fr",
        known_glossary_terms=["Sinistre"],
    )
    assert rep.passed is False
    assert rep.bound_routes_valid is False
    assert rep.ui_components_and_sections_valid is False
    assert rep.glossary_and_zero_secret_valid is False
    assert len(rep.violations) >= 4


@pytest.mark.asyncio
async def test_generate_and_attach_help_exports_git_invalidates_redis_and_blocks_observer(
    tmp_path: Path,
) -> None:
    fake_redis = _FakeRedis()
    svc = HelpGenerationAndHotAttachmentService(redis_client=fake_redis)

    with pytest.raises(ObserverModeReadOnlyError):
        await svc.generate_and_attach_help(
            article_id="help.claims.triage",
            article_slug="claims-triage",
            version="1.0.0",
            pack_slug="claims",
            title_fr="Triage",
            title_en="Triage",
            bound_routes=["/cockpit"],
            roles_allowed=["CONTRIBUTOR"],
            glossary_terms=["Sinistre"],
            related_workflows=["claims/triage"],
            purpose_fr="But",
            purpose_en="Purpose",
            steps_fr=["Étape 1"],
            steps_en=["Step 1"],
            faq_fr=["Q1"],
            faq_en=["Q1"],
            actor_role="READ_ONLY_OBSERVER",
        )

    res = await svc.generate_and_attach_help(
        article_id="help.claims.triage",
        article_slug="claims-triage",
        version="1.0.0",
        pack_slug="claims",
        title_fr="Aide Triage Sinistres",
        title_en="Claims Triage Help",
        bound_routes=["/cockpit"],
        roles_allowed=["CONTRIBUTOR"],
        glossary_terms=["Sinistre"],
        related_workflows=["claims/triage"],
        purpose_fr="Explique le triage.",
        purpose_en="Explains triage.",
        steps_fr=["Étape 1"],
        steps_en=["Step 1"],
        faq_fr=["Q1 ?"],
        faq_en=["Q1?"],
        known_glossary_terms=["Sinistre"],
        export_root_dir=tmp_path,
    )

    assert res.authority_role == "REFERENCE"
    assert res.hot_attach_elapsed_ms < 100.0
    assert "help:route:/cockpit:claims:fr" in fake_redis.deleted_keys
    assert "help:route:/cockpit:claims:en" in fake_redis.deleted_keys
    fr_file = tmp_path / "packages/orcia-pack-claims/help/fr/claims-triage.md"
    en_file = tmp_path / "packages/orcia-pack-claims/help/en/claims-triage.md"
    assert fr_file.is_file()
    assert en_file.is_file()

    with pytest.raises(HelpArticleValidationError):
        await svc.generate_and_attach_help(
            article_id="help.bad",
            article_slug="bad",
            version="1.0.0",
            pack_slug="core",
            title_fr="Bad",
            title_en="Bad",
            bound_routes=["/cockpit"],
            roles_allowed=["CONTRIBUTOR"],
            glossary_terms=["TermeNonAligne"],
            related_workflows=[],
            purpose_fr="But",
            purpose_en="Purpose",
            steps_fr=["Étape 1"],
            steps_en=["Step 1"],
            faq_fr=["Q1"],
            faq_en=["Q1"],
            known_glossary_terms=["TermeValideUnique"],
        )


@pytest.mark.asyncio
async def test_fastapi_process5_endpoints_validate_and_attach_help() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        gen_resp = await client.post(
            "/api/v1/pack-builder/processes/generate-and-attach-help",
            json={
                "article_id": "help.cockpit.overview",
                "article_slug": "cockpit-overview",
                "version": "1.0.0",
                "pack_slug": "core",
                "title_fr": "Vue d'ensemble du Cockpit",
                "title_en": "Cockpit Overview",
                "bound_routes": ["/cockpit"],
                "roles_allowed": ["CONTRIBUTOR", "ARCHITECT"],
                "glossary_terms": ["RunLock"],
                "related_workflows": ["core/onboarding"],
                "purpose_fr": "Piloter vos décisions en attente.",
                "purpose_en": "Drive your pending decisions.",
                "steps_fr": ["Consulter les cartes de briefing"],
                "steps_en": ["Review briefing cards"],
                "faq_fr": ["Comment filtrer par espace ?"],
                "faq_en": ["How to filter by workspace?"],
                "ui_component_name": "StreamlinedCockpitView",
                "trigger_regime": "STAGED_HUMAN_REVIEW",
                "known_glossary_terms": ["RunLock"],
                "actor_role": "ARCHITECT",
            },
        )
        assert gen_resp.status_code == 201
        body: dict[str, Any] = gen_resp.json()
        assert body["authority_role"] == "REFERENCE"
        assert body["validation_fr"]["passed"] is True
        assert body["validation_en"]["passed"] is True
        assert body[" exported_git_paths".strip()] == [
            "docs/help/fr/cockpit-overview.md",
            "docs/help/en/cockpit-overview.md",
        ]


@pytest.mark.asyncio
async def test_process6_generate_orcia_documentation_workflow_runs_4_steps(
    tmp_path: Path,
) -> None:
    """Verify Process 6 (`generate-orcia-documentation`) executes all 4 steps."""
    svc = HelpGenerationAndHotAttachmentService()
    with pytest.raises(ObserverModeReadOnlyError):
        await svc.run_generate_orcia_documentation_workflow(
            actor_role="READ_ONLY_OBSERVER",
            export_root_dir=tmp_path,
        )

    report = await svc.run_generate_orcia_documentation_workflow(
        actor_role="ARCHITECT",
        export_root_dir=tmp_path,
    )
    assert report.workflow_slug == "generate-orcia-documentation"
    assert report.workflow_uri == "orcia://pack-builder/workflows/generate-orcia-documentation"
    assert report.lead_agent_handle == "@Rédacteur-Documentation-Orcia"
    assert report.routes_inventoried_count >= 20
    assert len(report.steps) == 4
    assert [s.step_number for s in report.steps] == [1, 2, 3, 4]
    assert all(s.status == "COMPLETED" for s in report.steps)
    assert report.validation_fr.passed is True
    assert report.validation_en.passed is True
    assert "Guide Fonctionnel par Écran" in report.generated_markdown_fr
    assert "Architecture & Modèle Métier" in report.generated_markdown_fr
    assert "Questions Fréquentes (FAQ)" in report.generated_markdown_fr
    assert (tmp_path / "docs/help/fr/orcia-complete-documentation.md").is_file()
    assert (tmp_path / "docs/help/en/orcia-complete-documentation.md").is_file()
