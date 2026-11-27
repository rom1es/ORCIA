"""Helper mappers & request parsers for `/api/v1/packs` (`Story 31.2`, `<= 300 L`)."""

from __future__ import annotations

import base64
import binascii
from email.parser import BytesParser
from email.policy import default as email_default_policy
from typing import Any

from fastapi import Request

from orcia_api.dependencies import get_auth_service
from orcia_api.locales._router_locale_messages import get_router_copy
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.packs import PackImportRequest
from orcia_api.schemas.process_studio_v2 import (
    ConnectorRequirementHealthItemResponse,
    DeclarativePackSummaryResponse,
)
from orcia_connectors.protocol import ConnectorHealthStatus, OrciaConnectorProtocol
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.packs import (
    ApmPackCodec,
    LoadedPackBundleV2,
    PackInvalidArchiveError,
    PackManifestV2,
    PackScopeType,
    PackSlotSpec,
    QuickActionSpec,
    RequiredConnectorSpec,
)
from orcia_core.permissions.enterprise_connectors import EnterpriseConnectorRecord
from orcia_core.permissions.errors import ObserverModeReadOnlyError
from orcia_core.permissions.models import UserIdentity


def trace_id_for(request: Request) -> str:
    """Resolve active OpenTelemetry trace_id."""
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def enforce_pack_mutation_guard(
    request: Request,
    *,
    scope_type: PackScopeType | None = None,
    scope_id: str | None = None,
    persona_key: str | None = None,
) -> UserIdentity:
    """Reject observer actors globally and on workspace scopes (`HTTP 403`)."""
    user = resolve_request_user(request, persona_key=persona_key)
    hdr = (request.headers.get("x-orcia-access-mode") or "").strip().upper()
    if (
        hdr == "READ_ONLY_OBSERVER"
        or user.platform_role in ("OBSERVER", "READ_ONLY_OBSERVER", "BU_DIRECTOR")
        or "OBSERVER" in user.roles
        or "READ_ONLY_OBSERVER" in user.roles
    ):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    if scope_type == PackScopeType.WORKSPACE and scope_id:
        ws_access = get_auth_service(request).evaluator.resolve_workspace_access(user, scope_id)
        if ws_access is not None and ws_access.access_mode == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(instance=str(request.url.path))
    return user


def slots_to_required_connectors(
    raw_slots: list[dict[str, Any]],
    manifest_meta: dict[str, Any],
) -> list[RequiredConnectorSpec]:
    """Build `RequiredConnectorSpec` list from v2 `declared_slots` or legacy manifest."""
    if raw_slots:
        specs: list[RequiredConnectorSpec] = []
        for slot in raw_slots:
            if not isinstance(slot, dict):
                continue
            scheme = str(slot.get("scheme") or "mcp")
            ckind = str(slot.get("connector_kind") or f"mcp:{scheme}")
            scopes = slot.get("required_access") or ["read"]
            used_for = str(
                slot.get("description_fr")
                or slot.get("description_en")
                or slot.get("slot_key")
                or ckind
            )
            specs.append(
                RequiredConnectorSpec(
                    connector_type=ckind,
                    required_scopes=[str(s) for s in scopes]
                    if isinstance(scopes, list)
                    else ["read"],
                    used_for=used_for,
                )
            )
        return specs
    legacy_reqs = manifest_meta.get("required_connectors") or []
    if isinstance(legacy_reqs, list):
        return [
            RequiredConnectorSpec.model_validate(item)
            for item in legacy_reqs
            if isinstance(item, dict)
        ]
    return []


async def evaluate_connector_requirement(
    req_conn: RequiredConnectorSpec,
    adapters: dict[str, OrciaConnectorProtocol],
    pg_connectors: dict[str, EnterpriseConnectorRecord],
) -> ConnectorRequirementHealthItemResponse:
    """Probe live connector health combining PG18 state and connector adapter."""
    kind_key = req_conn.connector_type.removeprefix("mcp:").removeprefix("atlassian-").lower()
    pg_rec = pg_connectors.get(kind_key)
    if pg_rec is not None and not pg_rec.enabled:
        health = ConnectorHealthStatus(
            connector_type=req_conn.connector_type,
            ok=False,
            latency_ms=0,
            error_message=get_router_copy().connector_disabled.format(name=pg_rec.name),
        )
    elif (adapter := adapters.get(req_conn.connector_type)) is not None:
        health = await adapter.healthcheck()
    else:
        health = ConnectorHealthStatus(
            connector_type=req_conn.connector_type,
            ok=False,
            latency_ms=0,
            error_message="Connector not registered",
        )
    return ConnectorRequirementHealthItemResponse(
        connector_type=req_conn.connector_type,
        required_scopes=req_conn.required_scopes,
        used_for=req_conn.used_for,
        health=health,
    )


async def build_pack_summary_from_pg_row(
    row: dict[str, object],
    adapters: dict[str, OrciaConnectorProtocol],
    pg_connectors: dict[str, EnterpriseConnectorRecord],
) -> DeclarativePackSummaryResponse:
    """Convert a PG18 `declarative_pack_bundles` v2 row into `DeclarativePackSummaryResponse`."""
    manifest_raw = row.get("manifest")
    meta = dict(manifest_raw) if isinstance(manifest_raw, dict) else {}
    counts_raw = meta.get("counts")
    counts = dict(counts_raw) if isinstance(counts_raw, dict) else {}
    raw_slots_obj = row.get("declared_slots")
    raw_slots = (
        [dict(s) for s in raw_slots_obj if isinstance(s, dict)]
        if isinstance(raw_slots_obj, list)
        else []
    )
    req_conns = slots_to_required_connectors(raw_slots, meta)
    health_items = [
        await evaluate_connector_requirement(req_conn, adapters, pg_connectors)
        for req_conn in req_conns
    ]
    qa_raw = meta.get("quick_actions") or []
    quick_actions = (
        [QuickActionSpec.model_validate(q) for q in qa_raw if isinstance(q, dict)]
        if isinstance(qa_raw, list)
        else []
    )
    declared_slots = [PackSlotSpec.model_validate(s) for s in raw_slots]
    return DeclarativePackSummaryResponse(
        id=str(row.get("pack_id") or row.get("id") or ""),
        bundle_id=str(row.get("id") or ""),
        slug=str(row.get("slug") or ""),
        name=str(row.get("name") or ""),
        version=str(row.get("version") or "1.0.0"),
        description=str(row.get("description") or meta.get("description") or ""),
        rbac_namespace=str(row.get("rbac_namespace") or "default"),
        bundle_sha256=str(row.get("bundle_sha256") or ""),
        archive_sha256=str(row.get("archive_sha256") or row.get("bundle_sha256") or ""),
        bundle_kind=str(row.get("bundle_kind") or "SYSTEM"),
        scope_type=str(row.get("scope_type") or "GLOBAL"),
        scope_id=str(row.get("scope_id") or "global"),
        status=str(row.get("status") or "PUBLISHED"),
        cas_object_key=str(row["cas_object_key"]) if row.get("cas_object_key") else None,
        agents_count=int(counts.get("agents", 0)),
        skills_count=int(counts.get("skills", 0)),
        gates_count=int(counts.get("gates", 0)),
        vsm_count=int(counts.get("vsm", 0)),
        workflows_count=int(counts.get("workflows", 0)),
        agents_slugs=[str(x) for x in (meta.get("agents_slugs") or [])],
        skills_slugs=[str(x) for x in (meta.get("skills_slugs") or [])],
        gates_slugs=[str(x) for x in (meta.get("gates_slugs") or [])],
        declared_slots=declared_slots,
        required_connectors=req_conns,
        connector_health=health_items,
        quick_actions=quick_actions,
    )


def _parse_multipart_pack_body(
    raw_content_type: str,
    body: bytes,
) -> tuple[bytes, PackScopeType | None, str | None, bool]:
    mime_blob = f"Content-Type: {raw_content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("latin-1")
    msg = BytesParser(policy=email_default_policy).parsebytes(mime_blob + body)
    if not msg.is_multipart():
        raise PackInvalidArchiveError(detail_override="Malformed multipart pack upload.")
    zip_bytes: bytes | None = None
    fields: dict[str, str] = {}
    for part in msg.iter_parts():
        name = part.get_param("name", header="content-disposition")
        payload = part.get_payload(decode=True)
        raw_bytes = payload if isinstance(payload, bytes) else b""
        if name == "file":
            zip_bytes = raw_bytes
        elif isinstance(name, str):
            fields[name] = raw_bytes.decode("utf-8", errors="replace").strip()
    if zip_bytes is None:
        raise PackInvalidArchiveError(detail_override="Missing multipart 'file' .zip upload.")
    raw_scope = fields.get("scope_type", "").upper()
    scope_type = PackScopeType(raw_scope) if raw_scope else None
    raw_scope_id = fields.get("scope_id") or None
    raw_replace = fields.get("replace_draft", "false").lower()
    return zip_bytes, scope_type, raw_scope_id, raw_replace in ("1", "true", "yes")


async def parse_pack_import_payload(
    request: Request,
) -> tuple[bytes, PackScopeType | None, str | None, bool]:
    """Parse either multipart `.zip` upload or JSON `PackImportRequest`."""
    raw_ct = request.headers.get("content-type") or ""
    if "multipart/form-data" in raw_ct.lower():
        return _parse_multipart_pack_body(raw_ct, await request.body())

    try:
        raw_json = await request.json()
        parsed = PackImportRequest.model_validate(raw_json)
        zip_bytes = base64.b64decode(parsed.zip_base64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise PackInvalidArchiveError(
            detail_override=f"Invalid pack import payload: {exc}"
        ) from exc
    scope_type = PackScopeType(parsed.scope_type) if parsed.scope_type else None
    return zip_bytes, scope_type, parsed.scope_id, parsed.replace_draft


def synthesize_zip_from_pg_row(row: dict[str, object]) -> bytes:
    """Synthesize a fallback deterministic APM `.zip` directly from a PG18 bundle row."""
    manifest_raw = row.get("manifest")
    meta = dict(manifest_raw) if isinstance(manifest_raw, dict) else {}
    slots_raw = row.get("declared_slots")
    slots = (
        [PackSlotSpec.model_validate(s) for s in slots_raw if isinstance(s, dict)]
        if isinstance(slots_raw, list)
        else []
    )
    manifest = PackManifestV2(
        id=str(row.get("pack_id") or ""),
        slug=str(row.get("slug") or "pack"),
        name=str(row.get("name") or "Pack"),
        version=str(row.get("version") or "1.0.0"),
        description=str(row.get("description") or meta.get("description") or ""),
        rbac_namespace=str(row.get("rbac_namespace") or "default"),
        declared_slots=slots,
    )
    bundle = LoadedPackBundleV2(
        manifest=manifest,
        archive_sha256=str(row.get("archive_sha256") or ("0" * 64)),
    )
    return ApmPackCodec().encode_zip_bytes(bundle)


__all__ = [
    "build_pack_summary_from_pg_row",
    "enforce_pack_mutation_guard",
    "evaluate_connector_requirement",
    "parse_pack_import_payload",
    "slots_to_required_connectors",
    "synthesize_zip_from_pg_row",
    "trace_id_for",
]
