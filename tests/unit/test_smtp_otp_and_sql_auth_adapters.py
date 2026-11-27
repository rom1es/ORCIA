"""Async unit tests for SMTP OTP delivery (`send_login_email_otp`) without fake SQL."""

from __future__ import annotations

import smtplib
from typing import Any

import pytest

from orcia_core.bootstrap import InMemoryOtpEmailSink, send_login_email_otp
from orcia_core.bootstrap._internal import smtp_otp_delivery as smtp_mod
from orcia_core.permissions import PassthroughVaultCipher, SmtpConnectorRequiredForEmailOtpError

pytestmark = pytest.mark.story("17.3")


@pytest.mark.asyncio
async def test_send_login_email_otp_sink_real_smtp_and_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `send_login_email_otp` handles missing connector, sink, STARTTLS, SSL, and errors."""
    cipher = PassthroughVaultCipher(b"s" * 32)
    dummy_engine: Any = object()

    async def _missing_connector(*_a: Any, **_kw: Any) -> Any:
        raise SmtpConnectorRequiredForEmailOtpError(detail_override="No active SMTP connector")

    monkeypatch.setattr(smtp_mod, "load_active_smtp_connector", _missing_connector)
    with pytest.raises(SmtpConnectorRequiredForEmailOtpError):
        await send_login_email_otp(
            dummy_engine,
            cipher=cipher,
            recipient_email="claire@orcia.local",
            otp_code="123456",
        )

    active_cfg = smtp_mod._ActiveSmtpConfig(
        connector_id="c-1",
        connector_name="Relay SMTP",
        base_url="smtp://mail.orcia.local:587",
        username="mailer@orcia.local",
        password="app-pass",  # pragma: allowlist secret
        sender_email="mailer@orcia.local",
    )

    async def _get_cfg(*_a: Any, **_kw: Any) -> smtp_mod._ActiveSmtpConfig:
        return active_cfg

    monkeypatch.setattr(smtp_mod, "load_active_smtp_connector", _get_cfg)
    sink = InMemoryOtpEmailSink()
    used = await send_login_email_otp(
        dummy_engine,
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
        dummy_engine,
        cipher=cipher,
        recipient_email="alex@orcia.local",
        otp_code="222333",
        locale="en",
    )
    assert used_smtp == "Relay SMTP" and starttls_called is True
    assert login_calls == [("mailer@orcia.local", "app-pass")]
    assert "[ORCIA] Your 6-digit verification code: 222333" in str(sent_messages[0]["Subject"])

    active_cfg = smtp_mod._ActiveSmtpConfig(
        connector_id="c-1",
        connector_name="Relay SMTP",
        base_url="smtps://user:urlpass@smtps.orcia.local:465",  # pragma: allowlist secret
        username="user",
        password="urlpass",  # pragma: allowlist secret
        sender_email="user",
    )
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
    await send_login_email_otp(
        dummy_engine,
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
            dummy_engine,
            cipher=cipher,
            recipient_email="bob@orcia.local",
            otp_code="111222",
        )
