"""Asynchronous SMTP delivery adapter for 6-digit login OTP verification codes."""

from __future__ import annotations

import asyncio
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol
from urllib.parse import urlparse

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.bootstrap._internal.sql_enterprise_connectors import (
    ensure_enterprise_connectors_schema,
)
from orcia_core.observability.logging import get_logger
from orcia_core.permissions.auth_policy import EMAIL_OTP_TTL_SECONDS
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.enterprise_connectors_crypto import (
    extract_url_host,
    unpack_encrypted_secret,
)
from orcia_core.permissions.errors import SmtpConnectorRequiredForEmailOtpError

_logger = get_logger("orcia_core.bootstrap.smtp_otp_delivery")


@dataclass(frozen=True, slots=True)
class DispatchedEmailOtpMessage:
    """Structured record of an outgoing 6-digit login OTP email."""

    recipient_email: str
    otp_code: str
    connector_name: str
    smtp_url: str
    locale: str = "fr"


class OtpEmailSinkProtocol(Protocol):
    """Injectable sink protocol allowing integration/E2E tests to capture OTPs deterministically."""

    async def send(self, message: DispatchedEmailOtpMessage) -> None: ...


class InMemoryOtpEmailSink:
    """Deterministic in-memory sink recording dispatched email OTP codes for verification."""

    def __init__(self) -> None:
        self.messages: list[DispatchedEmailOtpMessage] = []

    async def send(self, message: DispatchedEmailOtpMessage) -> None:
        self.messages.append(message)


@dataclass(frozen=True, slots=True)
class _ActiveSmtpConfig:
    connector_id: str
    connector_name: str
    base_url: str
    username: str | None
    password: str | None
    sender_email: str


def _parse_smtp_credentials(
    *,
    base_url: str,
    plaintext_secret: str | None,
) -> tuple[str | None, str | None, str]:
    parsed = urlparse(base_url)
    url_user = parsed.username
    url_pass = parsed.password
    host = parsed.hostname or "localhost"
    sender = url_user if url_user and "@" in url_user else f"no-reply@{host}"

    username = url_user
    password = url_pass
    if plaintext_secret:
        if not username and ":" in plaintext_secret:
            maybe_user, maybe_pw = plaintext_secret.split(":", 1)
            username = maybe_user.strip() or None
            password = maybe_pw
            if username and "@" in username:
                sender = username
        else:
            password = plaintext_secret
    return username, password, sender


async def load_active_smtp_connector(
    engine: AsyncEngine,
    *,
    cipher: PassthroughVaultCipher,
    instance: str | None = None,
) -> _ActiveSmtpConfig:
    """Load the first active `SMTP_MAIL` enterprise connector from PostgreSQL 18."""
    async with engine.begin() as conn:
        await ensure_enterprise_connectors_schema(conn)
        row = (
            await conn.execute(
                sa.text(
                    """
                    SELECT id, name, base_url, encrypted_admin_secret
                    FROM enterprise_connectors
                    WHERE connector_kind = 'SMTP_MAIL' AND enabled = TRUE
                    ORDER BY created_at ASC, name ASC
                    LIMIT 1;
                    """
                )
            )
        ).fetchone()
    if row is None:
        raise SmtpConnectorRequiredForEmailOtpError(instance=instance)

    cid = str(row[0])
    name = str(row[1])
    base_url = str(row[2])
    encrypted = str(row[3]) if row[3] else None
    plaintext_secret: str | None = None
    if encrypted:
        plaintext_secret = unpack_encrypted_secret(
            cipher,
            owner_id=f"admin:{cid}",
            packed=encrypted,
            scheme="SMTP_MAIL",
            host=extract_url_host(base_url),
        )
    username, password, sender = _parse_smtp_credentials(
        base_url=base_url,
        plaintext_secret=plaintext_secret,
    )
    return _ActiveSmtpConfig(
        connector_id=cid,
        connector_name=name,
        base_url=base_url,
        username=username,
        password=password,
        sender_email=sender,
    )


def _build_otp_email_message(
    *,
    sender_email: str,
    recipient_email: str,
    otp_code: str,
    locale: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    ttl_minutes = max(1, EMAIL_OTP_TTL_SECONDS // 60)
    if locale.lower().startswith("en"):
        msg["Subject"] = f"[ORCIA] Your 6-digit verification code: {otp_code}"
        msg.set_content(
            f"Hello,\n\nYour ORCIA verification code is: {otp_code}\n\n"
            f"This code expires in {ttl_minutes} minutes. "
            "If you did not initiate this login, ignore this message.\n"
        )
    else:
        msg["Subject"] = f"[ORCIA] Votre code de vérification à 6 chiffres : {otp_code}"
        msg.set_content(
            f"Bonjour,\n\nVotre code de vérification ORCIA est : {otp_code}\n\n"
            f"Ce code est valable pendant {ttl_minutes} minutes. "
            "Si vous n'êtes pas à l'origine de cette connexion, ignorez ce message.\n"
        )
    return msg


def _send_smtp_blocking(cfg: _ActiveSmtpConfig, msg: EmailMessage) -> None:
    parsed = urlparse(cfg.base_url)
    scheme = (parsed.scheme or "smtp").lower()
    host = parsed.hostname or "localhost"
    default_port = 465 if scheme == "smtps" else 587
    port = parsed.port or default_port

    if scheme == "smtps":
        with smtplib.SMTP_SSL(host, port, timeout=10.0) as client:
            if cfg.username and cfg.password:
                client.login(cfg.username, cfg.password)
            client.send_message(msg)
        return

    with smtplib.SMTP(host, port, timeout=10.0) as client:
        client.ehlo()
        if client.has_extn("starttls"):
            client.starttls()
            client.ehlo()
        if cfg.username and cfg.password:
            client.login(cfg.username, cfg.password)
        client.send_message(msg)


async def send_login_email_otp(
    engine: AsyncEngine,
    *,
    cipher: PassthroughVaultCipher,
    recipient_email: str,
    otp_code: str,
    locale: str = "fr",
    otp_email_sink: OtpEmailSinkProtocol | None = None,
    instance: str | None = None,
) -> str:
    """Deliver a 6-digit login OTP using the active `SMTP_MAIL` connector (non-blocking)."""
    cfg = await load_active_smtp_connector(engine, cipher=cipher, instance=instance)
    if otp_email_sink is not None:
        await otp_email_sink.send(
            DispatchedEmailOtpMessage(
                recipient_email=recipient_email,
                otp_code=otp_code,
                connector_name=cfg.connector_name,
                smtp_url=cfg.base_url,
                locale=locale,
            )
        )
        return cfg.connector_name

    email_msg = _build_otp_email_message(
        sender_email=cfg.sender_email,
        recipient_email=recipient_email,
        otp_code=otp_code,
        locale=locale,
    )
    try:
        await asyncio.to_thread(_send_smtp_blocking, cfg, email_msg)
    except OSError as exc:
        _logger.warning(
            "smtp_otp_delivery_failed",
            connector_name=cfg.connector_name,
            smtp_host=urlparse(cfg.base_url).hostname or "",
            error_type=type(exc).__name__,
        )
        raise SmtpConnectorRequiredForEmailOtpError(instance=instance) from exc
    return cfg.connector_name
