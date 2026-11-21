"""Internal AES-256-GCM passthrough credential helpers for `AuthAndOrganizationService`."""

from __future__ import annotations

from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.errors import ObserverModeReadOnlyError, ResourceNotFoundError
from orcia_core.permissions.models import (
    DatasourceScheme,
    PassthroughCredentialRecord,
    UserIdentity,
)
from orcia_kernel.ids import new_uuid7_str


def encrypt_passthrough_record(
    vault_cipher: PassthroughVaultCipher,
    user: UserIdentity,
    *,
    connector_scheme: DatasourceScheme,
    target_host: str,
    plaintext_secret: str,
    instance: str | None = None,
) -> PassthroughCredentialRecord:
    """Encrypt and construct an immutable `PassthroughCredentialRecord`."""
    if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
        raise ObserverModeReadOnlyError(instance=instance)
    ciphertext_b64, nonce_b64 = vault_cipher.encrypt(
        user_id=user.id,
        plaintext_secret=plaintext_secret,
        connector_scheme=connector_scheme,
        target_host=target_host,
    )
    return PassthroughCredentialRecord(
        id=new_uuid7_str(),
        user_id=user.id,
        connector_scheme=connector_scheme,
        target_host=target_host,
        ciphertext_b64=ciphertext_b64,
        nonce_b64=nonce_b64,
        key_version=1,
    )


def decrypt_passthrough_record(
    vault_cipher: PassthroughVaultCipher,
    user: UserIdentity,
    record: PassthroughCredentialRecord | None,
) -> str:
    """Decrypt a stored Passthrough credential exclusively for its owning `user`."""
    if record is None:
        raise ResourceNotFoundError()
    return vault_cipher.decrypt(
        user_id=user.id,
        ciphertext_b64=record.ciphertext_b64,
        nonce_b64=record.nonce_b64,
        connector_scheme=record.connector_scheme,
        target_host=record.target_host,
        key_version=record.key_version,
    )
