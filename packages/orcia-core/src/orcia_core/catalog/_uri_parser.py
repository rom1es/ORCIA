"""Federated URI parser helper extracted from `cas_resolver.py` to honor file size caps."""

from __future__ import annotations

import re

from orcia_core.catalog.errors import ValidationDomainError
from orcia_core.catalog.models import ArchiveFormat, ParsedFederatedUri
from orcia_kernel.ports import (
    get_registered_connector,
    is_registered_connector_scheme,
    list_registered_connector_schemes,
)

HEX_SHA_RE = re.compile(r"^[0-9a-f]{6,64}$")
FULL_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def get_allowed_schemes() -> frozenset[str]:
    """Return dynamic set of registered connector schemes (`orcia_kernel.ports`, `AD-20`)."""
    return list_registered_connector_schemes()


def parse_federated_uri(raw_uri: str) -> ParsedFederatedUri:
    """Parse and validate a federated URI against the dynamic connector registry (`AD-5`)."""
    cleaned = raw_uri.strip()
    if "://" not in cleaned:
        raise ValidationDomainError(detail_override=f"Missing '://' in URI: {raw_uri!r}")
    if cleaned.lower().startswith("pack://"):
        cleaned = f"orcia://packs/{cleaned[7:].lstrip('/')}"
    scheme_raw, remainder = cleaned.split("://", 1)
    scheme_lower = scheme_raw.lower()
    if not is_registered_connector_scheme(scheme_lower):
        raise ValidationDomainError(detail_override=f"Unsupported URI scheme {scheme_raw!r}")
    remainder = remainder.strip()
    if "/" not in remainder:
        raise ValidationDomainError(detail_override=f"URI must include authority/path: {raw_uri!r}")
    authority, raw_path = [part.strip() for part in remainder.split("/", 1)]
    if not authority or not raw_path:
        raise ValidationDomainError(detail_override=f"Empty authority or path: {raw_uri!r}")

    connector = get_registered_connector(scheme_lower)
    resolution_mode = (
        connector.capabilities().version_resolution_mode
        if connector is not None
        else "ref_or_latest"
    )

    expected_sha256: str | None = None
    version_or_ref = "latest"
    path_part = raw_path
    if "@sha256:" in raw_path:
        path_part, sha_ref = raw_path.rsplit("@sha256:", 1)
        sha_clean = sha_ref.strip().lower()
        if not HEX_SHA_RE.match(sha_clean):
            raise ValidationDomainError(detail_override=f"Invalid @sha256 digest: {raw_uri!r}")
        expected_sha256 = sha_clean
        version_or_ref = f"sha256:{sha_clean[:12]}"
    elif "@" in raw_path:
        path_part, ref_part = raw_path.rsplit("@", 1)
        ref_clean = ref_part.strip()
        if not path_part.strip() or not ref_clean:
            raise ValidationDomainError(detail_override=f"Empty path or version ref: {raw_uri!r}")
        version_or_ref = ref_clean
    elif resolution_mode == "last_path_segment":
        segments = [seg for seg in path_part.split("/") if seg]
        version_or_ref = segments[-1] if segments else "latest"

    path_clean = path_part.strip().strip("/")
    if not path_clean:
        raise ValidationDomainError(detail_override=f"Empty normalized path: {raw_uri!r}")
    archive_format: ArchiveFormat = (
        "tar.gz"
        if path_clean.endswith((".tar.gz", ".tgz"))
        else ("zip" if path_clean.endswith(".zip") else "none")
    )
    return ParsedFederatedUri(
        raw_uri=cleaned,
        scheme=scheme_lower,
        authority=authority,
        path=path_clean,
        version_or_ref=version_or_ref,
        expected_sha256=expected_sha256,
        archive_format=archive_format,
    )
