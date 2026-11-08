"""Declarative Pack Loader & Workspace Pack Exporter (`orcia_core.packs.loader`).

Hot-loads 100% declarative packs (`packs/<domain>/`) containing only YAML and Markdown files,
with zero dynamic Python imports (`TASK-02` & `TASK-03`).
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

from orcia_core.workflows.schemas_v2 import ValueStreamMapSpec, WorkflowDefinitionV2


class RequiredConnectorSpec(BaseModel):
    connector_type: str = Field(..., description="Ex: mcp:enterprise-tracker")
    required_scopes: list[str] = Field(default_factory=lambda: ["read"])
    used_for: str


class QuickActionSpec(BaseModel):
    id: str
    label: str
    target_workflow_slug: str
    icon: str = "play"


class DeclarativePackManifest(BaseModel):
    """Schema for `packs/<pack_id>/pack.yaml` (100% declarative)."""

    id: str
    slug: str
    name: str
    version: str
    description: str
    rbac_namespace: str = Field(..., description="Ex: engineering, hr, finance, docs")
    required_connectors: list[RequiredConnectorSpec] = Field(default_factory=list)
    quick_actions: list[QuickActionSpec] = Field(default_factory=list)


class LoadedPackBundle(BaseModel):
    manifest: DeclarativePackManifest
    bundle_sha256: str
    glossary: dict[str, Any]
    agents_markdown: dict[str, str]
    skills_markdown: dict[str, str]
    gates_specs: dict[str, Any]
    vsm_specs: list[ValueStreamMapSpec]
    workflows: list[WorkflowDefinitionV2]


class DeclarativePackLoader:
    """Hot-loads `packs/<domain>/` directories without any dynamic Python import."""

    def __init__(self, packs_root_dir: Path) -> None:
        self.packs_root_dir = packs_root_dir

    def load_all_packs(self) -> dict[str, LoadedPackBundle]:
        if not self.packs_root_dir.exists():
            return {}
        bundles: dict[str, LoadedPackBundle] = {}
        for pack_dir in sorted(self.packs_root_dir.iterdir()):
            manifest_path = pack_dir / "pack.yaml"
            if pack_dir.is_dir() and manifest_path.exists():
                bundle = self.load_single_pack(pack_dir)
                bundles[bundle.manifest.id] = bundle
        return bundles

    def load_single_pack(self, pack_dir: Path) -> LoadedPackBundle:
        manifest_raw = yaml.safe_load((pack_dir / "pack.yaml").read_text(encoding="utf-8"))
        manifest = DeclarativePackManifest.model_validate(manifest_raw)

        hasher = hashlib.sha256()
        for file_path in sorted(pack_dir.rglob("*")):
            if file_path.is_file():
                hasher.update(file_path.read_bytes())

        glossary: dict[str, Any] = {}
        if (pack_dir / "glossary.yaml").exists():
            glossary = (
                yaml.safe_load((pack_dir / "glossary.yaml").read_text(encoding="utf-8")) or {}
            )

        agents_md = (
            {
                p.stem: p.read_text(encoding="utf-8")
                for p in sorted((pack_dir / "agents").glob("*.md"))
            }
            if (pack_dir / "agents").exists()
            else {}
        )

        skills_md = (
            {
                p.stem: p.read_text(encoding="utf-8")
                for p in sorted((pack_dir / "skills").glob("*.md"))
            }
            if (pack_dir / "skills").exists()
            else {}
        )

        gates_specs = (
            {
                p.stem: (
                    yaml.safe_load(p.read_text(encoding="utf-8"))
                    if p.suffix in (".yaml", ".yml")
                    else p.read_text(encoding="utf-8")
                )
                for p in sorted((pack_dir / "gates").glob("*"))
                if p.is_file()
            }
            if (pack_dir / "gates").exists()
            else {}
        )

        vsm_specs: list[ValueStreamMapSpec] = []
        workflows: list[WorkflowDefinitionV2] = []
        if (pack_dir / "workflows").exists():
            for wf_file in sorted((pack_dir / "workflows").glob("*.yaml")):
                data = yaml.safe_load(wf_file.read_text(encoding="utf-8"))
                if wf_file.name.startswith("vsm-"):
                    vsm_specs.append(ValueStreamMapSpec.model_validate(data))
                else:
                    workflows.append(WorkflowDefinitionV2.model_validate(data))

        return LoadedPackBundle(
            manifest=manifest,
            bundle_sha256=hasher.hexdigest(),
            glossary=glossary,
            agents_markdown=agents_md,
            skills_markdown=skills_md,
            gates_specs=gates_specs,
            vsm_specs=vsm_specs,
            workflows=workflows,
        )


class PackExporter:
    """Exports a workspace or pack bundle into a declarative `.zip` archive (`pack.yaml` + dirs)."""

    @staticmethod
    def export_bundle_to_zip_bytes(
        bundle: LoadedPackBundle,
        *,
        workspace_id: str | None = None,
    ) -> bytes:
        buf = io.BytesIO()
        root_prefix = bundle.manifest.slug
        manifest_dict = bundle.manifest.model_dump(mode="json")
        if workspace_id:
            manifest_dict["exported_from_workspace_id"] = workspace_id

        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                f"{root_prefix}/pack.yaml",
                yaml.safe_dump(manifest_dict, allow_unicode=True, sort_keys=False),
            )
            zf.writestr(
                f"{root_prefix}/glossary.yaml",
                yaml.safe_dump(bundle.glossary, allow_unicode=True, sort_keys=False),
            )
            for agent_slug, md in sorted(bundle.agents_markdown.items()):
                zf.writestr(f"{root_prefix}/agents/{agent_slug}.md", md)
            for skill_slug, md in sorted(bundle.skills_markdown.items()):
                zf.writestr(f"{root_prefix}/skills/{skill_slug}.md", md)
            for gate_slug, spec in sorted(bundle.gates_specs.items()):
                if isinstance(spec, str):
                    zf.writestr(f"{root_prefix}/gates/{gate_slug}.md", spec)
                else:
                    zf.writestr(
                        f"{root_prefix}/gates/{gate_slug}.yaml",
                        yaml.safe_dump(spec, allow_unicode=True, sort_keys=False),
                    )
            for vsm in bundle.vsm_specs:
                vsm_yaml = yaml.safe_dump(
                    vsm.model_dump(mode="json"), allow_unicode=True, sort_keys=False
                )
                zf.writestr(f"{root_prefix}/workflows/vsm-{vsm.slug}.yaml", vsm_yaml)
            for wf in bundle.workflows:
                wf_yaml = yaml.safe_dump(
                    wf.model_dump(mode="json"), allow_unicode=True, sort_keys=False
                )
                zf.writestr(f"{root_prefix}/workflows/{wf.slug}.yaml", wf_yaml)
        return buf.getvalue()


__all__ = [
    "DeclarativePackLoader",
    "DeclarativePackManifest",
    "LoadedPackBundle",
    "PackExporter",
    "QuickActionSpec",
    "RequiredConnectorSpec",
]
