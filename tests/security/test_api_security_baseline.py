"""TEST-09 — Socle Sécurité / Red-Team (couche `AD-17`) : garde-fous sans infrastructure.

Couvre : SSRF des endpoints de modèles IA (règle 4 de `AGENTS.md`), refus d'identités inconnues,
enveloppe RFC 9457 + `trace_id` sur les erreurs, et sondes de défauts connus (BUG-E2E-04).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.routers.assistant_llm_providers import is_safe_llm_endpoint_url


@pytest.fixture(scope="module")
def client() -> TestClient:
    import os

    os.environ.setdefault("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    os.environ.setdefault("ORCIA_USE_CASSETTE_LLM", "true")
    from orcia_api.main import create_app

    return TestClient(create_app(), raise_server_exceptions=False)


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.10.20:8080/v1",
        "http://[fe80::1]/v1",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://100.100.100.200/latest/meta-data/",
        "ftp://example.com/model",
        "file:///etc/passwd",
        "",
    ],
)
def test_ssrf_guard_blocks_metadata_and_non_http_endpoints(url: str) -> None:
    assert not is_safe_llm_endpoint_url(url)


@pytest.mark.parametrize(
    "url",
    ["https://api.openai.com/v1", "http://ollama.local:11434/v1", "http://llm.internal/v1"],
)
def test_ssrf_guard_allows_legitimate_internal_and_public_domains(url: str) -> None:
    assert is_safe_llm_endpoint_url(url)


def test_unknown_persona_is_rejected_not_fabricated(client: TestClient) -> None:
    res = client.get("/api/v1/inbox/notifications?persona_key=intrus-inexistant")
    assert res.status_code == 404
    assert res.headers["content-type"].startswith("application/problem+json")


def test_validation_errors_use_problem_details_with_trace_id(client: TestClient) -> None:
    res = client.post("/api/v1/bootstrap/welcome-setup/first-admin", json={"email": "x"})
    assert res.status_code == 422
    assert res.headers["content-type"].startswith("application/problem+json")
    body = res.json()
    assert body["error_code"] and len(body["trace_id"]) == 32


def test_missing_bearer_falls_back_to_default_persona_known_defect(client: TestClient) -> None:
    """BUG-E2E-04 : sans jeton, l'API retombe sur la persona `marc` (TEAM_LEAD).

    Ce test documente le défaut : il doit être INVERSÉ (attendre 401) quand le correctif
    « Bearer obligatoire hors mode test » sera livré.
    """
    res = client.get("/api/v1/inbox/notifications")
    assert res.status_code == 200, "défaut BUG-E2E-04 corrigé ? inverser ce test (attendre 401)"


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        (
            "PATCH",
            "/api/v1/control-center/workspaces/0192c4e0-0000-7000-8000-000000000201/lifecycle?persona_key=claire",
            {"lifecycle_phase": "BUILD"},
        ),
        (
            "POST",
            "/api/v1/control-center/runs/0195f000-0000-7000-8000-000000000701/steps/0195f000-0000-7000-8000-000000000801/mutate-check?persona_key=claire",
            {"action": "approve_gate"},
        ),
        (
            "POST",
            "/api/v1/agents-and-skills/agents?persona_key=claire",
            {
                "name": "Agent Intrus",
                "role_mission": "Ne doit pas pouvoir être créé par un observateur.",
                "instructions": "Interdit.",
            },
        ),
        (
            "POST",
            "/api/v1/agents-and-skills/skills?persona_key=claire",
            {
                "name": "Skill Intrus",
                "objective": "Ne doit pas pouvoir être créé par un observateur.",
                "instructions": "Interdit.",
            },
        ),
    ],
)
def test_observer_persona_claire_is_rejected_on_mutation_endpoints(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, object],
) -> None:
    """`RunAccessGuard` : `READ_ONLY_OBSERVER` rejeté en `403 ERR_OBSERVER_MODE_READ_ONLY`."""
    res = client.request(method, path, json=payload)
    assert res.status_code == 403, res.text
    assert res.headers["content-type"].startswith("application/problem+json")
    assert res.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"


def test_rbac_privilege_escalation_and_unauthorized_resource_lock(client: TestClient) -> None:
    """Confinement de délégation (`403 ERR_GRANT_ESCALATION_FORBIDDEN`) & verrou IAM."""
    eval_res = client.post(
        "/api/v1/settings/iam/evaluate",
        json={
            "subject_id": "0195f000-0000-7000-8000-000000000204",
            "subject_type": "USER",
            "roles": ["CONTRIBUTOR"],
            "scope_path": "org/orcia/bu/claims/team/alpha/workspace/ws-1/resource/res-secret",
            "title": "Connecteur Restreint",
            "context": {"env": "prod"},
            "require_secret_read": False,
            "require_execute": False,
        },
    )
    assert eval_res.status_code == 200
    assert eval_res.json()["locked"] is True

    # Requiring secret_config_read without authorization raises 403 ERR_SCOPE_ACCESS_DENIED
    secret_read_res = client.post(
        "/api/v1/settings/iam/evaluate",
        json={
            "subject_id": "0195f000-0000-7000-8000-000000000204",
            "subject_type": "USER",
            "roles": ["CONTRIBUTOR"],
            "scope_path": "org/orcia/bu/claims/team/alpha/workspace/ws-1/resource/res-secret",
            "title": "Connecteur Restreint",
            "context": {"env": "prod"},
            "require_secret_read": True,
            "require_execute": False,
        },
    )
    assert secret_read_res.status_code == 403
    assert secret_read_res.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

    # nadia (CONTRIBUTOR) cannot delegate `grant` or `admin` verbs
    esc_res = client.post(
        "/api/v1/settings/iam/grants",
        json={
            "actor_persona": "nadia",
            "subject_type": "USER",
            "subject_id": "0195f000-0000-7000-8000-000000000204",
            "scope_path": "org/orcia/bu/claims/team/alpha",
            "verbs": ["grant"],
            "effect": "ALLOW",
        },
    )
    assert esc_res.status_code == 403
    assert esc_res.json()["error_code"] == "ERR_GRANT_ESCALATION_FORBIDDEN"


def test_confidential_restricted_workspace_masks_business_payload_for_global_viewer(
    client: TestClient,
) -> None:
    """`AD-8` : un espace `CONFIDENTIAL_RESTRICTED` masque son payload métier."""
    ov_res = client.get("/api/v1/control-center/overview?scope_type=GLOBAL&persona_key=karim")
    assert ov_res.status_code == 200
    data = ov_res.json()
    ws3 = next(
        g
        for g in data["workspaces_governance"]
        if g["workspace_id"] == "0192c4e0-0000-7000-8000-000000000203"
    )
    assert ws3["visibility_mode"] == "CONFIDENTIAL_RESTRICTED"
    assert ws3["blackboard_payload_masked"] is True
    restricted_run = next(r for r in data["observer_runs"] if r["run_id"].endswith("0703"))
    assert restricted_run["blackboard_payload_masked"] is True


def test_canary_secret_is_never_returned_in_cleartext_on_settings_endpoints(
    client: TestClient,
) -> None:
    """`DEC-SEC-01` : un secret `secret_input` n'apparaît jamais en clair en HTTP."""
    canary = "CANARY_RED_TEAM_SECRET_999888"  # pragma: allowlist secret
    entries_resp = client.get("/api/v1/settings/entries")
    assert entries_resp.status_code == 200
    first_entry = entries_resp.json()[0]

    patch_resp = client.patch(
        "/api/v1/settings/entries",
        headers={"If-Match": first_entry["etag"]},
        json={
            "actor_persona": "karim",
            "scope_level": first_entry["scope_level"],
            "scope_id": first_entry["scope_id"],
            "category": first_entry["category"],
            "key": first_entry["key"],
            "value_jsonb": {"uri": "orcia://connectors/red-team-kb"},
            "secret_input": {
                "action": "set",
                "plaintext_value": canary,
            },
        },
    )
    assert patch_resp.status_code == 200
    assert canary not in patch_resp.text
    assert patch_resp.json()["secret_status"]["configured"] is True

    after_resp = client.get("/api/v1/settings/entries")
    assert after_resp.status_code == 200
    assert canary not in after_resp.text
