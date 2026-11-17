"""Targeted unit tests covering all Epic 7 architecture review fixes (`2026-11-17`)."""

from __future__ import annotations

import io
import json
import threading
from pathlib import Path

import pytest

from orcia_core.catalog.contextual_help import (
    ContextualHelpResolutionService,
    build_help_redis_cache_key,
)
from orcia_core.observability._internal.ecs_formatter import (
    clear_sensitive_secret_values,
    register_sensitive_secret_value,
    scrub_sensitive_text,
)
from orcia_core.permissions._autonomy_confinement import map_action_to_required_verb
from orcia_core.permissions.errors import WebhookSignatureInvalidError
from orcia_core.permissions.webhook_security import compute_webhook_hmac_sha256
from orcia_worker.sandbox_daemon import SandboxDaemonServer


def test_ecs_formatter_concurrent_secret_registry_thread_safe() -> None:
    """`MAJOR-02`: Concurrent register/scrub cycles must never raise RuntimeError."""
    clear_sensitive_secret_values()
    errors: list[Exception] = []

    def _writer(idx: int) -> None:
        try:
            for j in range(50):
                register_sensitive_secret_value(
                    f"secret-val-{idx}-{j}-token"  # pragma: allowlist secret
                )
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(exc)

    def _reader() -> None:
        try:
            for _ in range(100):
                res = scrub_sensitive_text("log contains secret-val-0-1-token here")
                assert isinstance(res, str)
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(exc)

    threads = [threading.Thread(target=_writer, args=(i,)) for i in range(4)] + [
        threading.Thread(target=_reader) for _ in range(4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    clear_sensitive_secret_values()
    assert errors == []


def test_sandbox_daemon_refuses_empty_token_outside_local_and_test(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`MAJOR-03`: Empty `internal_token` must fail fast in production/staging."""
    monkeypatch.setenv("ORCIA_ENV", "production")
    monkeypatch.delenv("ORCIA_SANDBOX_INTERNAL_TOKEN", raising=False)
    with pytest.raises(ValueError, match="ORCIA_SANDBOX_INTERNAL_TOKEN"):
        SandboxDaemonServer(internal_token="")

    monkeypatch.setenv("ORCIA_ENV", "local")
    srv = SandboxDaemonServer(internal_token="")
    assert srv.internal_token == ""


def test_manage_pipe_stream_to_rotating_log_live_rollover(tmp_path: Path) -> None:
    """`MAJOR-02`: Live stdout/stderr pipe must roll over when log exceeds `max_bytes`."""
    from scripts.manage import pipe_stream_to_rotating_log

    log_file = tmp_path / "api.log"
    payload = ("\n".join(f"line-{idx:04d}-" + ("x" * 64) for idx in range(60)) + "\n").encode()
    written = pipe_stream_to_rotating_log(
        io.BytesIO(payload),
        log_file,
        max_bytes=512,
        backup_count=2,
    )
    assert written == len(payload)
    assert log_file.exists()
    assert (tmp_path / "api.log.1").exists()


def test_minor_02_write_verb_confinement_and_pack_normalization() -> None:
    """`MINOR-02` & `MAJOR-01`: `:write` maps to `update` and `orcia-core` normalizes to `core`."""
    for act in ("catalog:write", "catalog.write", "write_catalog", "help_article:update"):
        assert map_action_to_required_verb(act) == "update"
    assert (
        build_help_redis_cache_key("/processes", "orcia-core", "fr")
        == "help:route:/processes:core:fr"
    )


@pytest.mark.asyncio
async def test_contextual_help_async_redis_await_and_corrupted_webhook_secret() -> None:
    """`MAJOR-01` & `BLOCKING-02`: Async Redis client awaited + undecryptable secret yields 401."""

    class _AsyncRedisStub:
        def __init__(self) -> None:
            self.store: dict[str, str] = {}
            self.deleted: list[str] = []

        async def get(self, key: str) -> str | None:
            return self.store.get(key)

        async def set(self, key: str, val: str, ex: int = 300) -> bool:
            del ex
            self.store[key] = val
            return True

        async def delete(self, key: str) -> int:
            self.deleted.append(key)
            return 1 if self.store.pop(key, None) is not None else 0

    redis_stub = _AsyncRedisStub()
    svc = ContextualHelpResolutionService(redis_client=redis_stub)
    res1 = await svc.resolve_for_route_async(
        route="/mes-espaces/$id/sources", pack="orcia-core", lang="fr"
    )
    assert res1.redis_cache_key == "help:route:/mes-espaces/$id/sources:core:fr"
    assert res1.cache_hit is False
    assert res1.redis_cache_key in redis_stub.store

    res2 = await svc.resolve_for_route_async(
        route="/mes-espaces/$id/sources", pack="core", lang="fr"
    )
    assert res2.cache_hit is True

    await svc.publish_hot_version_async(
        resource_id=res1.active_article.resource_id,
        new_version="9.9.9",
        new_title="Titre @v9.9.9",
        new_summary_what_for="Résumé",
        new_markdown_body="### Pas-à-pas\n1. OK",
    )
    assert res1.redis_cache_key in redis_stub.deleted

    # Verify 401 WebhookSignatureInvalidError on undecryptable webhook secret
    from orcia_core.orchestration.triggers_dispatcher import (
        CreateTriggerCommand,
        TriggerDispatcherService,
    )
    from orcia_core.permissions import (
        AutonomyContractService,
        HierarchicalRbacService,
        IamAccountRecord,
        SignAutonomyContractCommand,
        UserIdentity,
    )
    from orcia_core.permissions.crypto import PassthroughVaultCipher

    contracts = AutonomyContractService(rbac_service=HierarchicalRbacService())
    ws_id = "0192c4e0-0000-7000-8000-000000000201"
    signer = UserIdentity(
        id="u-lead",
        email="marc@orcia.io",
        display_name="Marc",
        auth_mode="LOCAL",
        human_profile_archetype="DEVELOPER",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
    )
    sp = IamAccountRecord(
        id="sp-1",
        principal_id="sp-1",
        display_name="SP",
        email=None,
        account_kind="SERVICE_PRINCIPAL",
        auth_source="SERVICE_TOKEN",
        roles=("TEAM_LEAD",),
        team_ids=(ws_id,),
    )
    await contracts.sign_contract(
        SignAutonomyContractCommand(
            workspace_id=ws_id,
            workflow_id="wf-1",
            workflow_version="1.0.0",
            workflow_sha256="a" * 64,
            criticality="STANDARD",
            service_principal_id=sp.id,
            allowed_read_sources=("catalog:read",),
            allowed_write_actions=("catalog:write",),
            max_cost_per_run_usd=5.0,
        ),
        signer=signer,
        service_principal=sp,
        allowed_scope_ids=(ws_id,),
    )
    dispatcher = TriggerDispatcherService(
        contract_service=contracts, vault_cipher=PassthroughVaultCipher("1" * 32)
    )
    trig = await dispatcher.create_trigger(
        CreateTriggerCommand(
            workspace_id=ws_id,
            workflow_id="wf-1",
            trigger_type="WEBHOOK",
            webhook_secret=None,
        )
    )
    dispatcher._secrets_enc[trig.id] = "corrupted-ciphertext"  # pragma: allowlist secret
    body = json.dumps({"delivery_key": "k1"}).encode()
    sig = compute_webhook_hmac_sha256(body, "wrong")
    with pytest.raises(WebhookSignatureInvalidError):
        await dispatcher.verify_webhook_request(
            trigger_id=trig.id,
            raw_body=body,
            signature_header=sig,
            delivery_key="k1",
        )
