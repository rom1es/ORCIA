"""Unit, HTTP Contract & PostgreSQL 18 SQL Adapter Tests for Agents (`🤖 Mes Agents`)
and Skills (`🛠️ Compétences`) Management, Attachment, Governance, and 1-Click Execution.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.catalog.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.orchestration import (
    AgentsAndSkillsManagementService,
    ManagedAgentRecord,
    ManagedSkillRecord,
)


def test_agents_and_skills_service_lifecycle_and_detachment() -> None:
    """Verify creating, attaching, executing, and deleting Skills & Agents in the domain service."""
    svc = AgentsAndSkillsManagementService()
    assert svc.skills == ()
    assert svc.agents == ()

    # 1. Create a reusable Skill
    skill = svc.upsert_skill(
        name="Audit Conformite Fournisseur",
        objective="Vérifier les clauses contractuelles critiques",
        input_parameters=["contrat", "annexe"],
        instructions="Contrôler le plafond de responsabilité et la clause de réversibilité.",
        expected_output_format="Tableau des écarts + recommandation",
    )
    assert skill.skill_id == "skill-audit-conformite-fournisseur"
    assert skill.command_handle == "/audit-conformite-fournisseur"
    assert skill.input_parameters == ("contrat", "annexe")
    assert skill.visibility_scope == "TEAM"
    assert skill.enabled_in_workspace is True

    # 2. Execute the Skill on a sample input
    skill_outcome = svc.execute_skill(
        skill.skill_id,
        input_text="Article 9 : responsabilité plafonnée à 5 000 EUR",
    )
    assert skill_outcome.skill_id == skill.skill_id
    assert "Audit Conformite Fournisseur" in skill_outcome.output_text
    assert "Article 9" in skill_outcome.output_text

    # 3. Create an Agent with the Skill attached
    agent = svc.upsert_agent(
        name="Analyste Achats",
        role_mission="Sécuriser les contrats IT et Cloud",
        instructions="Analyser rigoureusement chaque clause sensible.",
        thinking_level="complex",
        skill_ids=[skill.skill_id, "non-existent-skill"],
    )
    assert agent.agent_id == "agent-analyste-achats"
    assert agent.skill_ids == (skill.skill_id,)
    assert agent.visibility_scope == "TEAM"
    assert agent.enabled_in_workspace is True
    assert agent.mcp_exposed is False

    # 4. Execute the Agent and verify attached Skill is invoked
    agent_outcome = svc.execute_agent(
        agent.agent_id,
        prompt="Analyse le contrat SaaS AcmeCorp",
    )
    assert agent_outcome.agent_id == agent.agent_id
    assert len(agent_outcome.invoked_skills) == 1
    assert agent_outcome.invoked_skills[0].skill_id == skill.skill_id
    assert "Audit Conformite Fournisseur" in agent_outcome.response_text

    # 5. Toggle/detach skills via set_agent_skills
    updated_agent = svc.set_agent_skills(agent.agent_id, skill_ids=[])
    assert updated_agent.skill_ids == ()
    reattached_agent = svc.set_agent_skills(
        agent.agent_id,
        skill_ids=[skill.skill_id],
    )
    assert reattached_agent.skill_ids == (skill.skill_id,)

    # 6. Deleting the Skill automatically detaches it from the Agent
    deleted_skill, detached_from = svc.delete_skill(skill.skill_id)
    assert deleted_skill.skill_id == skill.skill_id
    assert detached_from == (agent.agent_id,)
    assert svc.get_agent(agent.agent_id).skill_ids == ()

    # 7. Deleting the Agent removes it cleanly
    deleted_agent = svc.delete_agent(agent.agent_id)
    assert deleted_agent.agent_id == agent.agent_id
    assert svc.agents == ()


def test_pack_immutability_duplication_and_governance_toggles() -> None:
    """Verify PACK agents/skills cannot be deleted, can be duplicated, and support toggles."""
    svc = AgentsAndSkillsManagementService()
    pack_skill = svc.upsert_skill(
        skill_id="skill-pack-dora",
        name="Controle DORA",
        objective="Vérifier la résilience opérationnelle numérique",
        instructions="Contrôler les registres ICT.",
        visibility_scope="PACK",
        source_pack_key="pack-conformite-dora",
    )
    pack_agent = svc.upsert_agent(
        agent_id="agent-pack-dora",
        name="Auditeur DORA Officiel",
        role_mission="Auditer la conformité DORA",
        instructions="Appliquer la grille officielle DORA.",
        thinking_level="complex",
        skill_ids=[pack_skill.skill_id],
        visibility_scope="PACK",
        source_pack_key="pack-conformite-dora",
    )

    with pytest.raises(ValidationDomainError) as exc_skill:
        svc.delete_skill(pack_skill.skill_id)
    assert "Pack Métier" in str(exc_skill.value)

    with pytest.raises(ValidationDomainError) as exc_agent:
        svc.delete_agent(pack_agent.agent_id)
    assert "Pack Métier" in str(exc_agent.value)

    # Duplicate pack agent into customizable PRIVATE or TEAM agent
    duplicated = svc.duplicate_agent(pack_agent.agent_id, visibility_scope="PRIVATE")
    assert duplicated.agent_id != pack_agent.agent_id
    assert duplicated.name == "Auditeur DORA Officiel (Copie)"
    assert duplicated.visibility_scope == "PRIVATE"
    assert duplicated.source_pack_key == "pack-conformite-dora"
    assert duplicated.skill_ids == (pack_skill.skill_id,)

    # Toggle workspace enablement and MCP exposure
    disabled = svc.set_agent_enabled(pack_agent.agent_id, enabled=False)
    assert disabled.enabled_in_workspace is False
    exposed = svc.set_agent_mcp_exposure(duplicated.agent_id, mcp_exposed=True)
    assert exposed.mcp_exposed is True

    # Duplicated non-PACK agent can be deleted
    removed_copy = svc.delete_agent(duplicated.agent_id)
    assert removed_copy.agent_id == duplicated.agent_id


def test_agents_and_skills_service_validation_and_sync() -> None:
    """Verify domain errors on invalid inputs, missing entities, and sync_from_records."""
    svc = AgentsAndSkillsManagementService()

    with pytest.raises(ValidationDomainError):
        svc.upsert_skill(name="  ", objective="desc", instructions="inst")

    with pytest.raises(ValidationDomainError):
        svc.upsert_agent(name="Agent X", role_mission="  ", instructions="inst")

    with pytest.raises(ResourceNotFoundError):
        svc.get_skill("skill-unknown")

    with pytest.raises(ResourceNotFoundError):
        svc.get_agent("agent-unknown")

    s1 = ManagedSkillRecord(
        skill_id="skill-1",
        slug="skill-1",
        command_handle="/skill-1",
        uri="orcia://skills/skill-1@1.0.0",
        name="Skill 1",
        objective="Obj 1",
        input_parameters=(),
        instructions="Inst 1",
        expected_output_format="Markdown",
    )
    a1 = ManagedAgentRecord(
        agent_id="agent-1",
        slug="agent-1",
        handle="@agent-1",
        uri="orcia://agents/agent-1@1.0.0",
        name="Agent 1",
        role_mission="Role 1",
        instructions="Inst A1",
        thinking_level="simple",
        skill_ids=("skill-1", "orphan-skill"),
    )
    svc.sync_from_records(skills=(s1,), agents=(a1,))
    assert svc.get_agent("agent-1").skill_ids == ("skill-1",)


def test_agents_and_skills_fastapi_router_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify all `/api/v1/agents-and-skills/*` HTTP endpoints and Observer Mode guard."""
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    client = TestClient(app)

    # 1. Day-0 initial state: 0 agents, 0 skills
    r0 = client.get("/api/v1/agents-and-skills")
    assert r0.status_code == 200
    assert r0.json()["agents"] == []
    assert r0.json()["skills"] == []

    # 2. Observer mode (claire) is rejected with 403 ERR_OBSERVER_MODE_READ_ONLY
    r_obs = client.post(
        "/api/v1/agents-and-skills/skills?persona_key=claire",
        json={
            "skill_id": "skill-test",
            "name": "Test Skill",
            "objective": "Objectif métier",
            "input_parameters": ["texte"],
            "instructions": "Instructions",
            "expected_output_format": "Markdown",
        },
    )
    assert r_obs.status_code == 403
    assert r_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    # 3. Create a Skill via POST /api/v1/agents-and-skills/skills
    r_skill = client.post(
        "/api/v1/agents-and-skills/skills",
        json={
            "skill_id": "skill-synthese-contrat",
            "name": "Synthese de contrat",
            "objective": "Identifier les engagements financiers et pénalités",
            "input_parameters": ["contrat", "conditions"],
            "instructions": "Extraire les montants, durées d'engagement et clauses de sortie.",
            "expected_output_format": "Fiche synthétique en 3 points",
        },
    )
    assert r_skill.status_code == 200
    assert r_skill.json()["command_handle"] == "/synthese-de-contrat"

    # 4. Execute the Skill
    r_exec_skill = client.post(
        "/api/v1/agents-and-skills/skills/skill-synthese-contrat/execute",
        json={"input_text": "Engagement ferme de 36 mois à 120 kEUR/an."},
    )
    assert r_exec_skill.status_code == 200
    assert "Synthese de contrat" in r_exec_skill.json()["output_text"]

    # 5. Create a PACK Agent and verify immutability, duplication, and governance PATCH
    r_pack_agent = client.post(
        "/api/v1/agents-and-skills/agents",
        json={
            "agent_id": "agent-pack-achats",
            "name": "Auditeur Pack Achats",
            "role_mission": "Vérifier les achats IT du Pack",
            "instructions": "Appliquer le référentiel Achats.",
            "thinking_level": "medium",
            "skill_ids": ["skill-synthese-contrat"],
            "visibility_scope": "PACK",
            "source_pack_key": "pack-achats-it",
        },
    )
    assert r_pack_agent.status_code == 200
    assert r_pack_agent.json()["visibility_scope"] == "PACK"

    # Deleting a PACK agent returns 422 ValidationDomainError
    r_del_pack = client.delete("/api/v1/agents-and-skills/agents/agent-pack-achats")
    assert r_del_pack.status_code == 422

    # Duplicate the PACK agent into a customizable TEAM agent
    r_dup = client.post(
        "/api/v1/agents-and-skills/agents/agent-pack-achats/duplicate",
        json={"new_name": "Contrôleur des Engagements", "visibility_scope": "TEAM"},
    )
    assert r_dup.status_code == 200
    dup_data = r_dup.json()
    dup_id = dup_data["agent_id"]
    assert dup_data["visibility_scope"] == "TEAM"
    assert dup_data["source_pack_key"] == "pack-achats-it"
    assert dup_data["skill_ids"] == ["skill-synthese-contrat"]

    # Toggle governance on the duplicated agent
    r_gov = client.patch(
        f"/api/v1/agents-and-skills/agents/{dup_id}/governance",
        json={
            "enabled_in_workspace": False,
            "mcp_exposed": True,
            "visibility_scope": "PRIVATE",
            "thinking_level": "complex",
        },
    )
    assert r_gov.status_code == 200
    gov_body = r_gov.json()
    assert gov_body["enabled_in_workspace"] is False
    assert gov_body["mcp_exposed"] is True
    assert gov_body["visibility_scope"] == "PRIVATE"
    assert gov_body["thinking_level"] == "complex"

    # 6. Execute the duplicated Agent
    r_exec_agent = client.post(
        f"/api/v1/agents-and-skills/agents/{dup_id}/execute",
        json={"prompt": "Peut-on signer ce contrat de 36 mois ?"},
    )
    assert r_exec_agent.status_code == 200
    assert len(r_exec_agent.json()["invoked_skills"]) == 1

    # 7. Delete the Skill -> verify automatic detachment
    r_del_skill = client.delete("/api/v1/agents-and-skills/skills/skill-synthese-contrat")
    assert r_del_skill.status_code == 200
    assert dup_id in r_del_skill.json()["detached_from_agent_ids"]

    # 8. Delete the duplicated Agent
    r_del_agent = client.delete(f"/api/v1/agents-and-skills/agents/{dup_id}")
    assert r_del_agent.status_code == 200
    assert r_del_agent.json()["deleted_id"] == dup_id


@pytest.mark.asyncio
async def test_agents_and_skills_postgres18_sql_adapter_queries() -> None:
    """Verify PostgreSQL 18 SQL adapter serialization/deserialization of all metadata fields."""
    import json
    from typing import Any
    from uuid import uuid4

    from orcia_core.orchestration import (
        delete_agent_from_postgres18,
        delete_skill_from_postgres18,
        load_agents_and_skills_from_postgres18,
        persist_agent_to_postgres18,
        persist_skill_to_postgres18,
    )

    root_org_id = uuid4()
    stored_rows: dict[str, tuple[Any, ...]] = {}

    class _FakeResult:
        def __init__(self, rows: list[tuple[Any, ...]]) -> None:
            self._rows = rows

        def first(self) -> tuple[Any, ...] | None:
            return self._rows[0] if self._rows else None

        def scalar_one(self) -> Any:
            return self._rows[0][0]

        def fetchall(self) -> list[tuple[Any, ...]]:
            return list(self._rows)

    class _FakeConn:
        async def __aenter__(self) -> _FakeConn:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def execute(self, stmt: object, params: dict[str, Any] | None = None) -> _FakeResult:
            sql = str(stmt)
            p = params or {}
            if "SELECT id FROM org_units" in sql:
                return _FakeResult([(root_org_id,)])
            if "INSERT INTO catalog_items" in sql:
                item_type = "USER_SKILL" if "'USER_SKILL'" in sql else "USER_AGENT"
                res_type = "skill" if "'skill'" in sql else "agent"
                stored_rows[p["resource_id"]] = (
                    p["resource_id"],
                    p["uri"],
                    p["title"],
                    p["description"],
                    res_type,
                    p["version"],
                    p["sha256"],
                    item_type,
                    json.loads(p["metadata_jsonb"]),
                )
                return _FakeResult([])
            if "SELECT resource_id, uri, title" in sql:
                return _FakeResult(list(stored_rows.values()))
            if "DELETE FROM catalog_items" in sql:
                stored_rows.pop(p["resource_id"], None)
                return _FakeResult([])
            return _FakeResult([])

    class _FakeEngine:
        def begin(self) -> _FakeConn:
            return _FakeConn()

        def connect(self) -> _FakeConn:
            return _FakeConn()

    engine: Any = _FakeEngine()
    svc = AgentsAndSkillsManagementService()
    skill = svc.upsert_skill(
        name="Verification Clauses RGPD",
        objective="Contrôler la conformité RGPD",
        input_parameters=["dpa"],
        instructions="Examiner l'article 28.",
        expected_output_format="Tableau RGPD",
        visibility_scope="PRIVATE",
        source_pack_key="pack-rgpd",
        enabled_in_workspace=False,
    )
    agent = svc.upsert_agent(
        name="DPO Assistant",
        role_mission="Assister le DPO sur les contrats",
        instructions="Signaler tout transfert hors UE.",
        thinking_level="complex",
        skill_ids=[skill.skill_id],
        visibility_scope="PACK",
        source_pack_key="pack-rgpd",
        enabled_in_workspace=False,
        mcp_exposed=True,
        agent_kind="REMOTE_MCP_A2A",
        remote_endpoint_url="https://mcp.internal/dpo-agent",
        posture="EVALUATOR_GATE",
        human_partner_role="SECURITY_QA",
        llm_model_tier="deep",
        temperature=0.0,
        max_tokens=8192,
        prompt_ref="git://rgpd-pack/prompts/dpo.md@main",
        invocation_modes=["generer", "corrections"],
        dialogue_mechanism="direct",
        allowed_rag_sources=["all_workspace_sources", "confluence_architecture"],
        ontology_views=["glossary", "securite_conformite"],
        mcp_tool_permissions={"search_tool": "READ_ONLY", "jira": "WRITE_PREVIEW"},
        guardrails=["citations_obligatoires", "filtrage_dcp_pii"],
        output_contract_format="gate_risk_json",
        write_preview_required=True,
        test_bench_validated=True,
    )

    await persist_skill_to_postgres18(engine, skill)
    await persist_agent_to_postgres18(engine, agent)

    loaded_skills, loaded_agents = await load_agents_and_skills_from_postgres18(engine)
    assert len(loaded_skills) == 1
    assert loaded_skills[0].skill_id == skill.skill_id
    assert loaded_skills[0].visibility_scope == "PRIVATE"
    assert loaded_skills[0].source_pack_key == "pack-rgpd"
    assert loaded_skills[0].enabled_in_workspace is False

    assert len(loaded_agents) == 1
    assert loaded_agents[0].agent_id == agent.agent_id
    assert loaded_agents[0].visibility_scope == "PACK"
    assert loaded_agents[0].source_pack_key == "pack-rgpd"
    assert loaded_agents[0].enabled_in_workspace is False
    assert loaded_agents[0].mcp_exposed is True
    assert loaded_agents[0].agent_kind == "REMOTE_MCP_A2A"
    assert loaded_agents[0].remote_endpoint_url == "https://mcp.internal/dpo-agent"
    assert loaded_agents[0].posture == "EVALUATOR_GATE"
    assert loaded_agents[0].human_partner_role == "SECURITY_QA"
    assert loaded_agents[0].llm_model_tier == "deep"
    assert loaded_agents[0].temperature == 0.0
    assert loaded_agents[0].max_tokens == 8192
    assert loaded_agents[0].prompt_ref == "git://rgpd-pack/prompts/dpo.md@main"
    assert loaded_agents[0].invocation_modes == ("generer", "corrections")
    assert loaded_agents[0].dialogue_mechanism == "direct"
    assert loaded_agents[0].allowed_rag_sources == (
        "all_workspace_sources",
        "confluence_architecture",
    )
    assert loaded_agents[0].ontology_views == ("glossary", "securite_conformite")
    assert dict(loaded_agents[0].mcp_tool_permissions) == {
        "search_tool": "READ_ONLY",
        "jira": "WRITE_PREVIEW",
    }
    assert loaded_agents[0].guardrails == ("citations_obligatoires", "filtrage_dcp_pii")
    assert loaded_agents[0].output_contract_format == "gate_risk_json"
    assert loaded_agents[0].write_preview_required is True
    assert loaded_agents[0].test_bench_validated is True

    _, detached_ids = svc.delete_skill(skill.skill_id)
    updated_agents = tuple(svc.get_agent(aid) for aid in detached_ids)
    await delete_skill_from_postgres18(engine, skill.skill_id, updated_agents)

    loaded_skills_after, loaded_agents_after = await load_agents_and_skills_from_postgres18(engine)
    assert loaded_skills_after == ()
    assert loaded_agents_after[0].skill_ids == ()

    await delete_agent_from_postgres18(engine, agent.agent_id)
    _, final_agents = await load_agents_and_skills_from_postgres18(engine)
    assert final_agents == ()
