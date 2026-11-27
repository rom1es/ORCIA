"""O(1) single-pass PII, tenant infra & secret export leak scanner (`Story 31.5`, `A3`)."""

from __future__ import annotations

import ipaddress
import re

from orcia_core.packs._internal._pack_export_infra_loader import (
    TenantInfraIdentifiers,
    load_tenant_infra_identifiers_conn,
)
from orcia_core.packs._internal._pack_export_infra_loader import (
    extract_host as _extract_host,
)
from orcia_core.packs.errors import PackPiiOrInfraLeakError

_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_GENERIC_URI_RE = re.compile(r"\b([a-z][a-z0-9+.-]{1,20})://([^\s\"'<>`)\]]+)", re.IGNORECASE)
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6_RE = re.compile(
    r"(?<![A-Za-z0-9:])(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}"
    r"(?:%[A-Za-z0-9_.-]+)?(?![A-Za-z0-9:])"
)
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("SECRET_REF", re.compile(r"vault://[^\s\"'<>]+", re.IGNORECASE)),
    ("BEARER_TOKEN", re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{12,}", re.IGNORECASE)),
    (
        "API_KEY_OR_TOKEN",
        re.compile(
            r"\b(?:sk-[A-Za-z0-9_\-]{16,}|ghp_[A-Za-z0-9]{16,}|gho_[A-Za-z0-9]{16,}|"
            r"glpat-[A-Za-z0-9_\-]{16,}|xox[bp]-[A-Za-z0-9\-]{16,}|AIza[0-9A-Za-z_\-]{20,}|"
            r"AKIA[0-9A-Z]{16}|pat_mcp_[A-Za-z0-9_\-]{12,})\b"
        ),
    ),
    ("PRIVATE_KEY_PEM", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "CREDENTIAL_LITERAL",
        re.compile(
            r"\b(?:api_key|api_secret|secret_key|access_token|client_secret|password)"
            r"\s*[:=]\s*['\"]?(?!\s*(?:\{\{|slot://|<redacted>|\"\"|''|null|none|true|false))"
            r"[^\s'\"#,;]{6,}",
            re.IGNORECASE,
        ),
    ),
)
_ALLOWED_SPEC_HOSTS: frozenset[str] = frozenset(
    {
        "json-schema.org",
        "www.json-schema.org",
        "spdx.org",
        "www.w3.org",
        "orcia.io",
        "example.com",
        "example.org",
    }
)
_PORTABLE_SCHEMES: frozenset[str] = frozenset({"slot", "catalog", "urn"})
_POLICY_WILDCARD_SCHEMES: frozenset[str] = frozenset({"git", "http", "https", "mcp", "ssh", "s3"})
_PRIVATE_HOST_SUFFIXES: tuple[str, ...] = (".internal", ".local", ".corp", ".lan", ".home")


def _is_forbidden_host_or_ip(host: str, tenant_hosts: frozenset[str]) -> bool:
    clean = host.strip().lower().strip("[]").split("%", 1)[0]
    if not clean or clean in _ALLOWED_SPEC_HOSTS:
        return False
    if clean in tenant_hosts or clean in ("localhost", "metadata.google.internal"):
        return True
    if any(clean.endswith(sfx) for sfx in _PRIVATE_HOST_SUFFIXES):
        return True
    try:
        ip_obj = ipaddress.ip_address(clean)
        return (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
            or str(ip_obj) == "100.100.100.200"
        )
    except ValueError:
        return False


def _is_forbidden_ipv6_literal(cand: str) -> bool:
    clean = cand.strip().strip("[]").split("%", 1)[0]
    try:
        ip_obj = ipaddress.IPv6Address(clean)
    except ValueError:
        return False
    return (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    )


def _scan_apm_yaml_emails(
    text: str, *, tenant_emails: frozenset[str], findings: list[dict[str, str]]
) -> None:
    in_authors_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line[0].isspace():
            key = stripped.split(":", 1)[0].strip().lower()
            in_authors_block = key in ("author", "authors", "maintainers")
            is_author_line = key == "author"
        else:
            is_author_line = in_authors_block and stripped.startswith(("- ", "email:", "name:"))
        for m in _EMAIL_RE.finditer(line):
            em = m.group(0).lower()
            if em in tenant_emails or not is_author_line:
                findings.append(
                    {
                        "path": "apm.yml",
                        "kind": "EMAIL_PII",
                        "detail": "Unauthorized email literal in manifest.",
                    }
                )
                return


def _is_forbidden_uri(
    scheme: str, remainder: str, *, rel_path: str, tenant_hosts: frozenset[str]
) -> bool:
    low_scheme = scheme.lower()
    if low_scheme in _PORTABLE_SCHEMES:
        return False
    if low_scheme == "orcia":
        return not remainder.lower().startswith("packs/")
    if low_scheme == "pack":
        return False
    full_uri = f"{low_scheme}://{remainder}"
    if low_scheme in ("http", "https"):
        return _is_forbidden_host_or_ip(_extract_host(full_uri), tenant_hosts)
    return not (
        rel_path.startswith("policies/")
        and rel_path.endswith(".policy.md")
        and low_scheme in _POLICY_WILDCARD_SCHEMES
        and "@" not in remainder
        and remainder.endswith("*")
        and not _is_forbidden_host_or_ip(_extract_host(full_uri), tenant_hosts)
    )


def scan_rendered_files_for_leaks(
    files: dict[str, bytes],
    infra: TenantInfraIdentifiers,
    *,
    instance: str | None = None,
) -> None:
    """Single-pass `O(bytes)` scan with `O(1)` set lookups; fail closed on any PII/infra leak."""
    findings: list[dict[str, str]] = []
    for rel_path in sorted(files.keys()):
        if rel_path == "apm.lock.yaml":
            continue
        text = files[rel_path].decode("utf-8", errors="replace")

        for um in _UUID_RE.finditer(text):
            if um.group(0).lower() in infra.tenant_uuids:
                findings.append(
                    {"path": rel_path, "kind": "TENANT_UUID", "detail": "Tenant UUID detected."}
                )
                break

        if rel_path == "apm.yml":
            _scan_apm_yaml_emails(text, tenant_emails=infra.tenant_emails, findings=findings)
        elif _EMAIL_RE.search(text):
            findings.append(
                {"path": rel_path, "kind": "EMAIL_PII", "detail": "Email literal detected."}
            )

        for uri_m in _GENERIC_URI_RE.finditer(text):
            if _is_forbidden_uri(
                uri_m.group(1), uri_m.group(2), rel_path=rel_path, tenant_hosts=infra.tenant_hosts
            ):
                findings.append(
                    {
                        "path": rel_path,
                        "kind": "PRIVATE_OR_INFRA_URI",
                        "detail": f"Blocked URI scheme/host in {rel_path}.",
                    }
                )
                break

        if any(
            _is_forbidden_host_or_ip(m.group(0), infra.tenant_hosts)
            for m in _IPV4_RE.finditer(text)
        ):
            findings.append(
                {"path": rel_path, "kind": "PRIVATE_OR_METADATA_IP", "detail": "Private IPv4."}
            )
        elif any(_is_forbidden_ipv6_literal(m.group(0)) for m in _IPV6_RE.finditer(text)):
            findings.append(
                {"path": rel_path, "kind": "PRIVATE_OR_METADATA_IP", "detail": "Private IPv6."}
            )

        for kind, pat in _SECRET_PATTERNS:
            if pat.search(text):
                findings.append(
                    {"path": rel_path, "kind": kind, "detail": f"Sensitive {kind.lower()} found."}
                )
                break

    if findings:
        raise PackPiiOrInfraLeakError(leak_findings=findings, instance=instance)


__all__ = [
    "TenantInfraIdentifiers",
    "load_tenant_infra_identifiers_conn",
    "scan_rendered_files_for_leaks",
]
