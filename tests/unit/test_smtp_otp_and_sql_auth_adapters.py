"""Async unit tests for SMTP OTP delivery, SQL Auth Policy & 2FA Login Challenges."""

from __future__ import annotations

import smtplib
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest

from orcia_core.bootstrap import (
    InMemoryOtpEmailSink,
    activate_user_totp_secret_on_postgres18,
    consume_login_challenge_on_postgres18,
    create_login_second_factor_challenge_on_postgres18,
    increment_challenge_attempts_on_postgres18,
    load_decrypted_oidc_client_secret,
    load_login_challenge_by_token_from_postgres18,
    load_platform_auth_policy_from_postgres18,
    send_login_email_otp,
    update_login_challenge_email_otp_on_postgres18,
    update_platform_auth_policy_on_postgres18,
)
from orcia_core.permissions import (
    PassthroughVaultCipher,
    SmtpConnectorRequiredForEmailOtpError,
    SsoConfigurationIncompleteError,
)
from orcia_core.permissions.enterprise_connectors_crypto import pack_encrypted_secret
from orcia_kernel.ids import new_uuid7_str


class _FakeMappingsResult:
    def __init__(self, mapping: dict[str, Any] | None) -> None:
        self._mapping = mapping

    def first(self) -> dict[str, Any] | None:
        return self._mapping


class _FakeResult:
    def __init__(
        self,
        *,
        row: tuple[Any, ...] | None = None,
        mapping: dict[str, Any] | None = None,
        rowcount: int = 0,
    ) -> None:
        self._row = row
        self._mapping = mapping
        self.rowcount = rowcount

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._row

    def mappings(self) -> _FakeMappingsResult:
        return _FakeMappingsResult(self._mapping)


class _FakeAsyncConnection:
    def __init__(self, handler: Callable[[str, dict[str, Any]], _FakeResult]) -> None:
        self._handler = handler

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        return self._handler(str(getattr(stmt, "text", stmt)), dict(params or {}))


class _FakeAsyncEngine:
    def __init__(self, conn: _FakeAsyncConnection) -> None:
        self._conn = conn

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[_FakeAsyncConnection]:
        yield self._conn


@pytest.mark.asyncio
async def test_send_login_email_otp_sink_real_smtp_and_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cipher = PassthroughVaultCipher(b"s" * 32)
    cid = new_uuid7_str()
    enc_pw = pack_encrypted_secret(
        cipher,
        owner_id=f"admin:{cid}",
        plaintext="mailer@orcia.local:app-pass",
        scheme="SMTP_MAIL",
        host="mail.orcia.local",
    )

    missing_engine: Any = _FakeAsyncEngine(_FakeAsyncConnection(lambda _s, _p: _FakeResult()))
    with pytest.raises(SmtpConnectorRequiredForEmailOtpError):
        await send_login_email_otp(
            missing_engine,
            cipher=cipher,
            recipient_email="claire@orcia.local",
            otp_code="123456",
        )

    active_url = "smtp://mail.orcia.local:587"
    active_enc: str | None = enc_pw

    def _smtp_handler(sql: str, _params: dict[str, Any]) -> _FakeResult:
        if "FROM enterprise_connectors" in sql:
            return _FakeResult(row=(cid, "Relay SMTP", active_url, active_enc))
        return _FakeResult()

    sink = InMemoryOtpEmailSink()
    ok_engine: Any = _FakeAsyncEngine(_FakeAsyncConnection(_smtp_handler))
    used = await send_login_email_otp(
        ok_engine,
        cipher=cipher,
        recipient_email="claire@orcia.local",
        otp_code="654321",
        locale="fr",
        otp_email_sink=sink,
    )
    assert used == "Relay SMTP"
    assert len(sink.messages) == 1 and sink.messages[0].otp_code == "654321"

    sent_messages: list[Any] = []
    login_calls: list[tuple[str, str]] = []
    starttls_called = False

    class _FakeSmtpClient:
        def __init__(self, host: str, port: int, timeout: float = 10.0) -> None:
            assert (host, port, timeout) == ("mail.orcia.local", 587, 10.0)

        def __enter__(self) -> _FakeSmtpClient:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def ehlo(self) -> None:
            return None

        def has_extn(self, name: str) -> bool:
            return name == "starttls"

        def starttls(self) -> None:
            nonlocal starttls_called
            starttls_called = True

        def login(self, user: str, password: str) -> None:
            login_calls.append((user, password))

        def send_message(self, msg: Any) -> None:
            sent_messages.append(msg)

    monkeypatch.setattr(smtplib, "SMTP", _FakeSmtpClient)
    used_smtp = await send_login_email_otp(
        ok_engine,
        cipher=cipher,
        recipient_email="alex@orcia.local",
        otp_code="222333",
        locale="en",
    )
    assert used_smtp == "Relay SMTP" and starttls_called is True
    assert login_calls == [("mailer@orcia.local", "app-pass")]
    assert "[ORCIA] Your 6-digit verification code: 222333" in str(sent_messages[0]["Subject"])

    active_url = "smtps://user:urlpass@smtps.orcia.local:465"  # pragma: allowlist secret
    active_enc = None
    ssl_events: list[Any] = []

    class _FakeSmtpSslClient:
        def __init__(self, host: str, port: int, timeout: float = 10.0) -> None:
            assert (host, port) == ("smtps.orcia.local", 465)

        def __enter__(self) -> _FakeSmtpSslClient:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def login(self, user: str, password: str) -> None:
            ssl_events.append((user, password))

        def send_message(self, msg: Any) -> None:
            ssl_events.append(msg)

    monkeypatch.setattr(smtplib, "SMTP_SSL", _FakeSmtpSslClient)
    ssl_engine: Any = _FakeAsyncEngine(_FakeAsyncConnection(_smtp_handler))
    await send_login_email_otp(
        ssl_engine,
        cipher=cipher,
        recipient_email="bob@orcia.local",
        otp_code="999888",
        locale="fr",
    )
    assert len(ssl_events) == 2

    def _failing_ssl(*_args: object, **_kwargs: object) -> Any:
        raise OSError("connection refused")

    monkeypatch.setattr(smtplib, "SMTP_SSL", _failing_ssl)
    with pytest.raises(SmtpConnectorRequiredForEmailOtpError):
        await send_login_email_otp(
            ssl_engine,
            cipher=cipher,
            recipient_email="bob@orcia.local",
            otp_code="111222",
        )


@pytest.mark.asyncio
async def test_sql_auth_policy_adapter_roundtrip() -> None:
    cipher = PassthroughVaultCipher(b"p" * 32)
    boot_epoch = UUID(new_uuid7_str())
    now = datetime.now(UTC)
    stored: dict[str, Any] = {
        "auth_mode": "LOCAL",
        "two_factor_mode": "NONE",
        "oidc_issuer_url": None,
        "oidc_client_id": None,
        "enc_secret": None,
        "secret_fp": None,
        "oidc_scopes": "openid profile email",
        "oidc_redirect_uri": None,
        "sso_button_label": None,
        "updated_by": None,
    }
    smtp_active = True

    def _row_tuple() -> tuple[Any, ...]:
        return (
            "GLOBAL",
            stored["auth_mode"],
            stored["two_factor_mode"],
            stored["oidc_issuer_url"],
            stored["oidc_client_id"],
            stored["enc_secret"],
            stored["secret_fp"],
            stored["oidc_scopes"],
            stored["oidc_redirect_uri"],
            stored["sso_button_label"],
            boot_epoch,
            stored["updated_by"],
            now,
        )

    def _policy_handler(sql: str, params: dict[str, Any]) -> _FakeResult:
        if "FROM enterprise_connectors" in sql:
            return _FakeResult(row=("SMTP Corporatif",) if smtp_active else None)
        if "FROM platform_auth_settings" in sql and "SELECT singleton_key" in sql:
            return _FakeResult(row=_row_tuple())
        if "UPDATE platform_auth_settings" in sql:
            for k in (
                "auth_mode",
                "two_factor_mode",
                "oidc_issuer_url",
                "oidc_client_id",
                "enc_secret",
                "secret_fp",
                "oidc_scopes",
                "oidc_redirect_uri",
                "sso_button_label",
                "updated_by",
            ):
                stored[k] = params[k]
            return _FakeResult(row=_row_tuple())
        return _FakeResult()

    engine: Any = _FakeAsyncEngine(_FakeAsyncConnection(_policy_handler))
    initial = await load_platform_auth_policy_from_postgres18(engine)
    assert (initial.auth_mode, initial.two_factor_mode, initial.smtp_connector_configured) == (
        "LOCAL",
        "NONE",
        True,
    )

    updated_sso = await update_platform_auth_policy_on_postgres18(
        engine,
        cipher=cipher,
        auth_mode="SSO",
        two_factor_mode="NONE",
        oidc_issuer_url="https://idp.orcia.local",
        oidc_client_id="orcia-web",
        oidc_client_secret="oidc-top-secret-xyz",  # pragma: allowlist secret
        oidc_redirect_uri="https://app.orcia.local/login",
        sso_button_label="SSO Organisation",
        updated_by="admin@orcia.local",
    )
    assert updated_sso.auth_mode == "SSO"
    assert updated_sso.oidc_client_secret_configured is True
    assert updated_sso.oidc_client_secret_fingerprint is not None

    loaded_state, decrypted_secret = await load_decrypted_oidc_client_secret(engine, cipher=cipher)
    assert loaded_state.oidc_client_id == "orcia-web"
    assert decrypted_secret == "oidc-top-secret-xyz"  # pragma: allowlist secret

    cleared = await update_platform_auth_policy_on_postgres18(
        engine,
        cipher=cipher,
        auth_mode="LOCAL",
        two_factor_mode="TOTP",
        clear_oidc_client_secret=True,
        updated_by="admin@orcia.local",
    )
    assert (cleared.auth_mode, cleared.two_factor_mode, cleared.oidc_client_secret_configured) == (
        "LOCAL",
        "TOTP",
        False,
    )

    smtp_active = False
    with pytest.raises(SmtpConnectorRequiredForEmailOtpError):
        await update_platform_auth_policy_on_postgres18(
            engine, cipher=cipher, auth_mode="LOCAL", two_factor_mode="EMAIL_OTP"
        )
    with pytest.raises(SsoConfigurationIncompleteError):
        await update_platform_auth_policy_on_postgres18(
            engine, cipher=cipher, auth_mode="SSO", two_factor_mode="NONE"
        )


@pytest.mark.asyncio
async def test_sql_login_challenges_adapter_lifecycle() -> None:
    uid = new_uuid7_str()
    saved: dict[str, Any] = {}
    totp_updates: list[dict[str, Any]] = []

    def _challenge_handler(sql: str, params: dict[str, Any]) -> _FakeResult:
        if "INSERT INTO auth_login_challenges" in sql:
            saved.clear()
            saved.update(
                {
                    "id": params["id"],
                    "user_id": params["user_id"],
                    "challenge_token_hash": params["token_hash"],
                    "challenge_kind": params["kind"],
                    "otp_code_hash": params["otp_hash"],
                    "pending_totp_secret_encrypted": params["pending_totp"],
                    "masked_destination": params["masked_dest"],
                    "attempts_count": 0,
                    "max_attempts": params["max_attempts"],
                    "expires_at": params["expires_at"],
                    "consumed_at": None,
                }
            )
            return _FakeResult(mapping=dict(saved))
        if "FROM auth_login_challenges" in sql:
            hit = params.get("token_hash") == saved.get("challenge_token_hash")
            return _FakeResult(mapping=dict(saved) if hit else None)
        if "SET attempts_count = attempts_count + 1" in sql:
            saved["attempts_count"] += 1
            return _FakeResult(row=(saved["attempts_count"],))
        if "SET consumed_at = NOW()" in sql:
            if saved.get("consumed_at") is None:
                saved["consumed_at"] = datetime.now(UTC)
                return _FakeResult(rowcount=1)
            return _FakeResult(rowcount=0)
        if "SET otp_code_hash = :otp_hash" in sql:
            saved["otp_code_hash"] = params["otp_hash"]
            saved["attempts_count"] = 0
            saved["expires_at"] = params["expires_at"]
            return _FakeResult(mapping=dict(saved))
        if "UPDATE users" in sql and "totp_enabled = TRUE" in sql:
            totp_updates.append(dict(params))
            return _FakeResult(rowcount=1)
        return _FakeResult()

    engine: Any = _FakeAsyncEngine(_FakeAsyncConnection(_challenge_handler))
    rec, raw_tok = await create_login_second_factor_challenge_on_postgres18(
        engine,
        user_id=uid,
        challenge_kind="EMAIL_OTP",
        otp_code="135790",
        masked_destination="a***n@orcia.local",
    )
    assert rec.challenge_kind == "EMAIL_OTP" and rec.otp_code_hash is not None
    assert await load_login_challenge_by_token_from_postgres18(engine, challenge_token=" ") is None
    loaded = await load_login_challenge_by_token_from_postgres18(engine, challenge_token=raw_tok)
    assert loaded is not None and loaded.id == rec.id
    assert await increment_challenge_attempts_on_postgres18(engine, challenge_id=rec.id) == 1
    refreshed = await update_login_challenge_email_otp_on_postgres18(
        engine, challenge_id=rec.id, new_otp_code="246810", ttl_seconds=300
    )
    assert refreshed is not None and refreshed.attempts_count == 0
    assert await consume_login_challenge_on_postgres18(engine, challenge_id=rec.id) is True
    assert await consume_login_challenge_on_postgres18(engine, challenge_id=rec.id) is False
    await activate_user_totp_secret_on_postgres18(
        engine, user_id=uid, encrypted_totp_secret="v1:encrypted"
    )
    assert len(totp_updates) == 1
    assert totp_updates[0]["secret_enc"] == "v1:encrypted"  # pragma: allowlist secret
