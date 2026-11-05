"""Unit, HTTP Contract & PostgreSQL 18 SQL Adapter Tests for Agents (`🤖 Mes Agents`)
and Skills (`🛠️ Compétences`) Management, Attachment, and 1-Click Execution.
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


def test_agents_and_skills_service_validation_and_sync() -> None:
    """Verify domain errors on invalid inputs, missing entities, and sync_from_records."""
    svc = AgentsAndSkillsManagementService()

    with pytest.raises(ValidationDomainError):
        svc.upsert_skill(
            name="  ",
            objective="desc",
            instructions="inst",
        )

    with pytest.raises(ValidationDomainError):
        svc.upsert_agent(
            name="Agent X",
            role_mission="  ",
            instructions="inst",
        )

    with pytest.raises(ResourceNotFoundError):
        svc.get_skill("skill-unknown")

    with pytest.raises(ResourceNotFoundError):
        svc.get_agent("agent-unknown")

    # Test sync_from_records filters orphan skill_ids
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
    """Verify all 8 `/api/v1/agents-and-skills/*` HTTP endpoints and Observer Mode guard."""
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    client = TestClient(app)

    # 1. Day-0 initial state: 0 agents, 0 skills
    r0 = client.get("/api/v1/agents-and-skills")
    assert r0.status_code == 200
    body0 = r0.json()
    assert body0["agents"] == []
    assert body0["skills"] == []

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
    skill_data = r_skill.json()
    assert skill_data["skill_id"] == "skill-synthese-contrat"
    assert skill_data["command_handle"] == "/synthese-de-contrat"

    # 4. Execute the Skill via POST /api/v1/agents-and-skills/skills/{skill_id}/execute
    r_exec_skill = client.post(
        "/api/v1/agents-and-skills/skills/skill-synthese-contrat/execute",
        json={"input_text": "Engagement ferme de 36 mois à 120 kEUR/an."},
    )
    assert r_exec_skill.status_code == 200
    exec_skill_body = r_exec_skill.json()
    assert exec_skill_body["skill_id"] == "skill-synthese-contrat"
    assert "Synthese de contrat" in exec_skill_body["output_text"]

    # 5. Create an Agent via POST /api/v1/agents-and-skills/agents
    r_agent = client.post(
        "/api/v1/agents-and-skills/agents",
        json={
            "agent_id": "agent-controleur-engagements",
            "name": "Contrôleur des Engagements",
            "role_mission": "Valider les engagements pluriannuels avant signature",
            "instructions": "Vérifier le budget et signaler tout engagement > 24 mois.",
            "thinking_level": "medium",
            "skill_ids": ["skill-synthese-contrat"],
        },
    )
    assert r_agent.status_code == 200
    agent_data = r_agent.json()
    assert agent_data["agent_id"] == "agent-controleur-engagements"
    assert agent_data["skill_ids"] == ["skill-synthese-contrat"]

    # 6. Execute the Agent via POST /api/v1/agents-and-skills/agents/{agent_id}/execute
    r_exec_agent = client.post(
        "/api/v1/agents-and-skills/agents/agent-controleur-engagements/execute",
        json={"prompt": "Peut-on signer ce contrat de 36 mois ?"},
    )
    assert r_exec_agent.status_code == 200
    exec_agent_body = r_exec_agent.json()
    assert exec_agent_body["agent_id"] == "agent-controleur-engagements"
    assert len(exec_agent_body["invoked_skills"]) == 1
    assert exec_agent_body["invoked_skills"][0]["skill_id"] == "skill-synthese-contrat"
    assert "Contrôleur des Engagements" in exec_agent_body["response_text"]

    # 7. Update Agent skills via PATCH /api/v1/agents-and-skills/agents/{agent_id}/skills
    r_patch = client.patch(
        "/api/v1/agents-and-skills/agents/agent-controleur-engagements/skills",
        json={"skill_ids": []},
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["skill_ids"] == []

    # Re-attach and then delete the Skill -> verify automatic detachment
    client.patch(
        "/api/v1/agents-and-skills/agents/agent-controleur-engagements/skills",
        json={"skill_ids": ["skill-synthese-contrat"]},
    )
    r_del_skill = client.delete("/api/v1/agents-and-skills/skills/skill-synthese-contrat")
    assert r_del_skill.status_code == 200
    assert r_del_skill.json()["deleted_id"] == "skill-synthese-contrat"
    assert r_del_skill.json()["detached_from_agent_ids"] == ["agent-controleur-engagements"]

    r_list_after = client.get("/api/v1/agents-and-skills")
    assert r_list_after.status_code == 200
    assert r_list_after.json()["skills"] == []
    assert r_list_after.json()["agents"][0]["skill_ids"] == []

    # 8. Delete the Agent
    r_del_agent = client.delete("/api/v1/agents-and-skills/agents/agent-controleur-engagements")
    assert r_del_agent.status_code == 200
    assert r_del_agent.json()["deleted_id"] == "agent-controleur-engagements"
    final_list = client.get("/api/v1/agents-and-skills").json()
    assert final_list["agents"] == []
    assert final_list["skills"] == []


@pytest.mark.asyncio
async def test_agents_and_skills_postgres18_sql_adapter_queries() -> None:
    """Verify PostgreSQL 18 SQL adapter functions (`persist_skill_to_postgres18`,
    `persist_agent_to_postgres18`, `load_agents_and_skills_from_postgres18`,
    `delete_skill_from_postgres18`, `delete_agent_from_postgres18`).
    """
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
    )
    agent = svc.upsert_agent(
        name="DPO Assistant",
        role_mission="Assister le DPO sur les contrats",
        instructions="Signaler tout transfert hors UE.",
        thinking_level="complex",
        skill_ids=[skill.skill_id],
    )

    await persist_skill_to_postgres18(engine, skill)
    await persist_agent_to_postgres18(engine, agent)

    loaded_skills, loaded_agents = await load_agents_and_skills_from_postgres18(engine)
    assert len(loaded_skills) == 1
    assert loaded_skills[0].skill_id == skill.skill_id
    assert loaded_skills[0].input_parameters == ("dpa",)
    assert len(loaded_agents) == 1
    assert loaded_agents[0].agent_id == agent.agent_id
    assert loaded_agents[0].skill_ids == (skill.skill_id,)

    _, detached_ids = svc.delete_skill(skill.skill_id)
    updated_agents = tuple(svc.get_agent(aid) for aid in detached_ids)
    await delete_skill_from_postgres18(engine, skill.skill_id, updated_agents)

    loaded_skills_after, loaded_agents_after = await load_agents_and_skills_from_postgres18(engine)
    assert loaded_skills_after == ()
    assert loaded_agents_after[0].skill_ids == ()

    await delete_agent_from_postgres18(engine, agent.agent_id)
    _, final_agents = await load_agents_and_skills_from_postgres18(engine)
    assert final_agents == ()
