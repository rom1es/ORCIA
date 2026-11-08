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
