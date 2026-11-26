"""FastAPI `Depends` providers for declarative packs v2 & import service (`Story 31.2`)."""

from __future__ import annotations

import os

from fastapi import Request

from orcia_api.dependencies._core_providers import get_configured_db_engine
from orcia_core.packs import (
    PackCasStoragePort,
    PackImportService,
    SeaweedFsPackCasAdapter,
    SqlPackBundleV2Repository,
)


def get_pack_cas_storage(request: Request) -> PackCasStoragePort | None:
    """Return configured SeaweedFS CAS adapter for packs when S3 endpoint is set."""
    existing: PackCasStoragePort | None = getattr(request.app.state, "pack_cas_storage", None)
    if existing is not None:
        return existing
    s3_ep = (
        getattr(request.app.state, "seaweedfs_endpoint_url", None)
        or os.environ.get("ORCIA_SEAWEEDFS_ENDPOINT_URL")
        or os.environ.get("SEAWEEDFS_ENDPOINT_URL")
        or os.environ.get("S3_ENDPOINT_URL")
        or ""
    ).strip()
    if not s3_ep:
        return None
    adapter = SeaweedFsPackCasAdapter(
        endpoint_url=s3_ep,
        bucket_name=os.environ.get("S3_BUCKET_NAME", "orcia-cas").strip() or "orcia-cas",
        access_key=os.environ.get("S3_ACCESS_KEY_ID", "orcia_seaweed").strip() or "orcia_seaweed",
        secret_key=os.environ.get(
            "S3_SECRET_ACCESS_KEY",
            "orcia_seaweed_secret",  # pragma: allowlist secret
        ).strip()
        or "orcia_seaweed_secret",  # pragma: allowlist secret
        http_client=getattr(request.app.state, "http_client", None),
    )
    request.app.state.pack_cas_storage = adapter
    return adapter


def get_pack_bundle_v2_repository(request: Request) -> SqlPackBundleV2Repository:
    """Return `SqlPackBundleV2Repository` wired to PG18 `db_engine`."""
    engine = get_configured_db_engine(request)
    repo: SqlPackBundleV2Repository | None = getattr(
        request.app.state, "pack_bundle_v2_repository", None
    )
    if repo is None:
        repo = SqlPackBundleV2Repository(engine)
        request.app.state.pack_bundle_v2_repository = repo
    elif engine is not None and getattr(repo, "_engine", None) is None:
        repo.set_engine(engine)
    return repo


def get_pack_import_service(request: Request) -> PackImportService:
    """Return `PackImportService` wired to PG18 `db_engine` and SeaweedFS CAS."""
    engine = get_configured_db_engine(request)
    cas_storage = get_pack_cas_storage(request)
    repo = get_pack_bundle_v2_repository(request)
    svc: PackImportService | None = getattr(request.app.state, "pack_import_service", None)
    if svc is None:
        svc = PackImportService(engine=engine, cas_storage=cas_storage, bundle_repository=repo)
        request.app.state.pack_import_service = svc
    else:
        if engine is not None and getattr(svc, "_engine", None) is None:
            svc.set_engine(engine)
        if cas_storage is not None and getattr(svc, "_cas_storage", None) is None:
            svc.set_cas_storage(cas_storage)
    return svc


__all__ = [
    "get_pack_bundle_v2_repository",
    "get_pack_cas_storage",
    "get_pack_import_service",
]
