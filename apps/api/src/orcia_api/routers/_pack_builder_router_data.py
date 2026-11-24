"""Installed business packs catalog builder for pack-builder router (`Story 27.7`)."""

from __future__ import annotations

from orcia_api.locales._router_locale_messages import get_router_copy
from orcia_api.schemas.pack_builder import (
    InstalledBusinessPackItemResponse,
    InstalledBusinessPackListResponse,
)
from orcia_core.orchestration.pack_builder_processes import PackBuilderSystemService
from orcia_pack_builder import PACK_BUILDER_AGENTS, PACK_BUILDER_PROCESSES
from orcia_pack_builder import __version__ as pack_builder_version
from orcia_pack_sdlc import __version__ as pack_sdlc_version


def build_installed_business_packs(
    svc: PackBuilderSystemService,
) -> InstalledBusinessPackListResponse:
    """Return the localized catalog of Business Packs installed and known in the ORCIA backend."""
    fr_copy = get_router_copy("fr")
    en_copy = get_router_copy("en")
    installed: list[InstalledBusinessPackItemResponse] = [
        InstalledBusinessPackItemResponse(
            pack_key="orcia-pack-sdlc",
            pack_slug="sdlc",
            title=fr_copy.pack_sdlc_title,
            title_en=en_copy.pack_sdlc_title,
            version=pack_sdlc_version or "1.0.0",
            domain_name=fr_copy.pack_sdlc_domain,
            description=fr_copy.pack_sdlc_desc,
            description_en=en_copy.pack_sdlc_desc,
            workflows_count=4,
            agents_count=6,
            is_system_pack=True,
        ),
        InstalledBusinessPackItemResponse(
            pack_key="orcia-pack-builder",
            pack_slug="pack-builder",
            title=fr_copy.pack_builder_title,
            title_en=en_copy.pack_builder_title,
            version=pack_builder_version or "1.0.0",
            domain_name=fr_copy.pack_builder_domain,
            description=fr_copy.pack_builder_desc,
            description_en=en_copy.pack_builder_desc,
            workflows_count=len(PACK_BUILDER_PROCESSES),
            agents_count=len(PACK_BUILDER_AGENTS),
            is_system_pack=True,
        ),
    ]
    seen_keys = {item.pack_key for item in installed}
    for custom in svc.list_created_packs():
        custom_key = f"orcia-pack-{custom.pack_slug}"
        if custom_key in seen_keys:
            continue
        seen_keys.add(custom_key)
        installed.append(
            InstalledBusinessPackItemResponse(
                pack_key=custom_key,
                pack_slug=custom.pack_slug,
                title=custom.title,
                title_en=custom.title,
                version=custom.version,
                domain_name=fr_copy.pack_custom_domain,
                description=custom.human_anchor_intent,
                description_en=custom.human_anchor_intent,
                workflows_count=max(1, custom.starlark_rules_certified_count),
                agents_count=1,
                is_system_pack=False,
            )
        )
    return InstalledBusinessPackListResponse(packs=installed)
