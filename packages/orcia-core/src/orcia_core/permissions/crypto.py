"""Cryptographic primitives for Story 1.2: Argon2id, TOTP (RFC 6238), AES-256-GCM & JWT."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import struct
import time
from dataclasses import dataclass
from typing import Any, Literal

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from Crypto.Cipher import AES

from orcia_core.domain.exceptions import (
    InvalidCredentialsError,
    RevokedTokenError,
    ValidationDomainError,
)
from orcia_core.domain.identifiers import new_uuid7_str

ACCESS_TOKEN_TTL_SECONDS: int = 900  # 15 minutes (AD-6)
REFRESH_TOKEN_TTL_SECONDS: int = 86400 * 7  # 7 days


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * ((4 - len(segment) % 4) % 4)
    return base64.urlsafe_b64decode((segment + padding).encode("ascii"))


class Argon2idPasswordHasher:
    """OWASP-compliant Argon2id password hasher for local authentication (AD-6)."""

    def __init__(
        self, *, time_cost: int = 2, memory_cost: int = 19456, parallelism: int = 1
    ) -> None:
        self._hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=32,
            salt_len=16,
        )

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password using Argon2id."""
        if not password or not password.strip():
            raise ValidationDomainError(detail_override="Password must not be empty.")
        return str(self._hasher.hash(password))

    def verify_password(self, password_hash: str, candidate_password: str) -> bool:
        """Verify a candidate password against an Argon2id hash in constant time."""
        if not password_hash or not candidate_password:
            return False
        try:
            return bool(self._hasher.verify(password_hash, candidate_password))
        except (VerifyMismatchError, InvalidHashError, VerificationError):
            return False


class TotpManager:
    """RFC 6238 TOTP generator and verifier (6 digits, 30s step, HMAC-SHA1)."""

    @staticmethod
    def generate_secret() -> str:
        """Generate a random 160-bit Base32 TOTP secret."""
        return base64.b32encode(os.urandom(20)).decode("ascii").rstrip("=")

    @staticmethod
    def generate_code(
        secret_b32: str, *, timestamp: int | None = None, step_seconds: int = 30, digits: int = 6
    ) -> str:
        """Compute the RFC 6238 TOTP code for `secret_b32` at `timestamp`."""
        cleaned = secret_b32.strip().upper().replace(" ", "")
        if not cleaned:
            raise ValidationDomainError(detail_override="TOTP secret must not be empty.")
        padding = "=" * ((8 - len(cleaned) % 8) % 8)
        try:
            key = base64.b32decode((cleaned + padding).encode("ascii"), casefold=True)
        except (binascii.Error, UnicodeEncodeError) as exc:
            raise ValidationDomainError(detail_override="Invalid Base32 TOTP secret.") from exc
        ts = int(time.time()) if timestamp is None else int(timestamp)
        digest = hmac.new(key, struct.pack(">Q", ts // step_seconds), hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        code_int = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % (10**digits)
        return str(code_int).zfill(digits)

    @classmethod
    def verify_code(
        cls,
        secret_b32: str,
        candidate_code: str,
        *,
        timestamp: int | None = None,
        valid_window: int = 1,
        step_seconds: int = 30,
    ) -> bool:
        """Verify a 6-digit TOTP code within `[-valid_window, +valid_window]` steps."""
        normalized = candidate_code.strip()
        if len(normalized) != 6 or not normalized.isdigit():
            return False
        ts = int(time.time()) if timestamp is None else int(timestamp)
        for delta in range(-valid_window, valid_window + 1):
            expected = cls.generate_code(
                secret_b32, timestamp=ts + delta * step_seconds, step_seconds=step_seconds
            )
            if hmac.compare_digest(expected, normalized):
                return True
        return False


class PassthroughVaultCipher:
    """AES-256-GCM authenticated encryption with per-user HKDF-SHA256 key derivation (NFR-SEC-4)."""

    def __init__(self, master_key: bytes | str) -> None:
        raw = master_key.encode("utf-8") if isinstance(master_key, str) else bytes(master_key)
        if len(raw) < 16:
            raise ValueError("PassthroughVaultCipher master_key must be at least 16 bytes.")
        self._master_key = raw

    def _derive_user_key(self, user_id: str, key_version: int = 1) -> bytes:
        salt = f"orcia-passthrough-hkdf-v{key_version}".encode()
        prk = hmac.new(salt, self._master_key, hashlib.sha256).digest()
        info = f"orcia:passthrough:user:{user_id}\x01".encode()
        return hmac.new(prk, info, hashlib.sha256).digest()

    def encrypt(
        self,
        user_id: str,
        plaintext_secret: str,
        *,
        connector_scheme: str = "git",
        target_host: str = "default",
        key_version: int = 1,
    ) -> tuple[str, str]:
        """Encrypt `plaintext_secret` with AES-256-GCM and return `(ciphertext_b64, nonce_b64)`."""
        if not user_id.strip() or not plaintext_secret.strip():
            msg = "user_id and plaintext_secret must not be empty."
            raise ValidationDomainError(detail_override=msg)
        nonce = os.urandom(12)
        cipher = AES.new(self._derive_user_key(user_id, key_version), AES.MODE_GCM, nonce=nonce)
        cipher.update(f"{user_id}|{connector_scheme}|{target_host}|v{key_version}".encode())
        ct, tag = cipher.encrypt_and_digest(plaintext_secret.encode("utf-8"))
        return base64.b64encode(ct + tag).decode("ascii"), base64.b64encode(nonce).decode("ascii")

    def decrypt(
        self,
        user_id: str,
        ciphertext_b64: str,
        nonce_b64: str,
        *,
        connector_scheme: str = "git",
        target_host: str = "default",
        key_version: int = 1,
    ) -> str:
        """Decrypt and authenticate an AES-256-GCM secret bound to `(user_id, scheme, host)`."""
        try:
            combined = base64.b64decode(ciphertext_b64.encode("ascii"), validate=True)
            nonce = base64.b64decode(nonce_b64.encode("ascii"), validate=True)
        except (binascii.Error, ValueError, UnicodeEncodeError) as exc:
            msg = "Malformed base64 ciphertext or nonce."
            raise ValidationDomainError(detail_override=msg) from exc
        if len(nonce) != 12 or len(combined) <= 16:
            msg = "Invalid AES-256-GCM nonce or authentication tag length."
            raise ValidationDomainError(detail_override=msg)
        cipher = AES.new(self._derive_user_key(user_id, key_version), AES.MODE_GCM, nonce=nonce)
        cipher.update(f"{user_id}|{connector_scheme}|{target_host}|v{key_version}".encode())
        try:
            return cipher.decrypt_and_verify(combined[:-16], combined[-16:]).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            msg = "AES-256-GCM authentication tag verification failed."
            raise ValidationDomainError(detail_override=msg) from exc


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """Verified claims extracted from a signed ORCIA JWT access or refresh token."""

    sub: str
    email: str
    role: str
    org_unit_id: str
    archetype: str
    auth_mode: str
    jti: str
    token_type: Literal["access", "refresh"]
    iat: int
    exp: int


@dataclass(frozen=True, slots=True)
class SessionTokenPair:
    """Short-lived access JWT (15 min) + revocable refresh token pair (AD-6)."""

    access_token: str
    refresh_token: str
    refresh_jti: str
    access_jti: str
    expires_in_seconds: int = ACCESS_TOKEN_TTL_SECONDS


class JwtSessionManager:
    """HMAC-SHA256 JWT issuer and verifier with 15-minute access TTL and `jti` tracking."""

    def __init__(self, signing_secret: str) -> None:
        if len(signing_secret.encode("utf-8")) < 16:
            raise ValueError("JWT signing_secret must be at least 16 bytes.")
        self._secret = signing_secret.encode("utf-8")

    def _encode_jwt(self, payload: dict[str, Any]) -> str:
        hdr = json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":"), sort_keys=True)
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        signing_str = f"{_b64url_encode(hdr.encode())}.{_b64url_encode(body.encode())}"
        sig = hmac.new(self._secret, signing_str.encode("ascii"), hashlib.sha256).digest()
        return f"{signing_str}.{_b64url_encode(sig)}"

    def issue_token_pair(
        self,
        *,
        user_id: str,
        email: str,
        role: str,
        org_unit_id: str,
        archetype: str,
        auth_mode: str,
        now_ts: int | None = None,
        access_ttl_seconds: int = ACCESS_TOKEN_TTL_SECONDS,
        refresh_ttl_seconds: int = REFRESH_TOKEN_TTL_SECONDS,
    ) -> SessionTokenPair:
        """Issue a 15-minute JWT access token and a revocable refresh token with UUIDv7 `jti`."""
        iat = int(time.time()) if now_ts is None else int(now_ts)
        acc_jti, ref_jti = new_uuid7_str(), new_uuid7_str()
        base = dict(
            sub=user_id,
            email=email,
            role=role,
            org_unit_id=org_unit_id,
            archetype=archetype,
            auth_mode=auth_mode,
            iat=iat,
        )
        acc = {**base, "jti": acc_jti, "token_type": "access", "exp": iat + access_ttl_seconds}
        ref = {**base, "jti": ref_jti, "token_type": "refresh", "exp": iat + refresh_ttl_seconds}
        return SessionTokenPair(
            self._encode_jwt(acc), self._encode_jwt(ref), ref_jti, acc_jti, access_ttl_seconds
        )

    def verify_token(
        self,
        token: str,
        *,
        expected_type: Literal["access", "refresh"] = "access",
        now_ts: int | None = None,
    ) -> TokenClaims:
        """Verify JWT signature, expiration, and token type (`access` vs `refresh`)."""
        parts = token.strip().split(".")
        if len(parts) != 3:
            raise InvalidCredentialsError()
        header_b64, payload_b64, sig_b64 = parts
        try:
            signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
            expected_sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
            actual_sig = _b64url_decode(sig_b64)
            payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        except (binascii.Error, ValueError, UnicodeDecodeError, UnicodeEncodeError) as exc:
            raise InvalidCredentialsError() from exc
        sig_ok = hmac.compare_digest(expected_sig, actual_sig)
        if not sig_ok or payload.get("token_type") != expected_type:
            raise InvalidCredentialsError()
        exp = int(payload.get("exp", 0))
        if exp <= (int(time.time()) if now_ts is None else int(now_ts)):
            raise RevokedTokenError()
        return TokenClaims(
            str(payload["sub"]),
            str(payload["email"]),
            str(payload["role"]),
            str(payload["org_unit_id"]),
            str(payload["archetype"]),
            str(payload["auth_mode"]),
            str(payload["jti"]),
            expected_type,
            int(payload["iat"]),
            exp,
        )
