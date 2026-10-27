"""BmadSkillPackAdapter: Lossless import of BMAD Skill Packs (`SKILL.md` + `customize.toml`, AR-5).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import io
import json
import re
import tarfile
import tomllib
import zipfile
from dataclasses import replace
from typing import Any, cast

from orcia_core.catalog.cas_resolver import (
    FederatedUriResolver,
    compute_bytes_sha256,
    parse_federated_uri,
)
from orcia_core.catalog.errors import ValidationDomainError
from orcia_core.catalog.models import (
    AdaptiveGatePolicy,
    BmadSkillPackInput,
    BmadSkillStepFile,
    CatalogItemEntity,
    EvaluationLensDefinition,
    ScalarValue,
    WorkflowDefinitionEntity,
    WorkflowStepDefinition,
)
from orcia_core.catalog.override_merger import compute_workflow_sha256
from orcia_kernel.ids import new_uuid7_str

HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n([\s\S]*))?$")


def _parse_skill_frontmatter(skill_markdown: str) -> tuple[dict[str, str], str]:
    text = skill_markdown.strip()
    if not text.startswith("---"):
        raise ValidationDomainError(
            detail_override="BMAD SKILL.md must start with YAML frontmatter ('---')"
        )
    match = FRONTMATTER_RE.match(text)
    if match is None:
        raise ValidationDomainError(
            detail_override="BMAD SKILL.md frontmatter is missing closing '---' delimiter"
        )
    meta: dict[str, str] = {}
    for line in match.group(1).strip().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, val = stripped.split(":", 1)
        meta[key.strip()] = val.strip().strip("'").strip('"')
    if not meta.get("name") or not meta.get("description"):
        raise ValidationDomainError(
            detail_override="BMAD SKILL.md frontmatter must define 'name' and 'description'"
        )
    return meta, (match.group(2) or "").strip()


def _parse_customize_toml(raw_toml: str) -> dict[str, Any]:
    cleaned = raw_toml.strip()
    if not cleaned:
        return {}
    try:
        return tomllib.loads(cleaned)
    except tomllib.TOMLDecodeError as exc:
        raise ValidationDomainError(
            detail_override=f"Invalid customize.toml in BMAD skill pack: {exc}"
        ) from exc


def _extract_step_definition(step_file: BmadSkillStepFile, index: int) -> WorkflowStepDefinition:
    filename = step_file.filename.strip().rsplit("/", 1)[-1]
    content = step_file.content_markdown.strip()
    if not filename or not content:
        raise ValidationDomainError(
            detail_override=f"BMAD step #{index} must have non-empty filename and content"
        )
    stem = filename.removesuffix(".md")
    heading_match = HEADING_RE.search(content)
    title = heading_match.group(1).strip() if heading_match else stem
    human_required = (
        "human_authored_required: true" in content.lower()
        or "ancrage humain obligatoire" in content.lower()
    )
    return WorkflowStepDefinition(
        step_key=stem, title=title, instructions=content, human_authored_required=human_required
    )


def _is_bmad_archive_entry(norm_path: str) -> bool:
    return (
        norm_path in ("SKILL.md", "customize.toml")
        or norm_path.endswith(("/SKILL.md", "/customize.toml"))
        or ("/steps/" in f"/{norm_path}" and norm_path.endswith(".md"))
    )


class BmadSkillPackAdapter:
    """Adapter converting a BMAD Skill Pack (`SKILL.md` + `customize.toml`) into ORCIA entities."""

    @classmethod
    def import_pack(
        cls,
        pack: BmadSkillPackInput,
        *,
        resolver: FederatedUriResolver | None = None,
    ) -> tuple[CatalogItemEntity, WorkflowDefinitionEntity]:
        """Convert `BmadSkillPackInput` losslessly into catalog and workflow entities."""
        parsed_uri = parse_federated_uri(pack.uri)
        frontmatter, skill_body = _parse_skill_frontmatter(pack.skill_markdown)
        customize_data = _parse_customize_toml(pack.customize_toml)
        slug = re.sub(r"[^a-z0-9-]+", "-", frontmatter["name"].lower()).strip("-")
        if not slug:
            raise ValidationDomainError(
                detail_override="BMAD skill name must contain at least one ASCII alphanumeric char"
            )
        if not pack.steps:
            raise ValidationDomainError(
                detail_override="BMAD skill pack must contain at least one step in steps/*.md"
            )

        sorted_step_files = sorted(pack.steps, key=lambda item: item.filename)
        steps = tuple(
            _extract_step_definition(step_file, idx)
            for idx, step_file in enumerate(sorted_step_files, start=1)
        )
        raw_scalars = customize_data.get("scalars", {})
        scalars_dict = raw_scalars if isinstance(raw_scalars, dict) else {}
        scalars: dict[str, ScalarValue] = {
            "skill_name": frontmatter["name"],
            "skill_body_markdown": skill_body,
            **{
                str(k): v for k, v in scalars_dict.items() if isinstance(v, (str, int, float, bool))
            },
        }

        def _str_tuple(key: str) -> tuple[str, ...]:
            raw = customize_data.get(key) or scalars_dict.get(key, [])
            return tuple(str(x) for x in raw if isinstance(x, str)) if isinstance(raw, list) else ()

        raw_lenses = customize_data.get("lenses", [])
        lenses = tuple(
            EvaluationLensDefinition(
                code=str(item["code"]),
                weight=float(item.get("weight", 0.5)),
                threshold=float(item.get("threshold", 0.8)),
            )
            for item in (raw_lenses if isinstance(raw_lenses, list) else [])
            if isinstance(item, dict) and "code" in item
        )

        version = str(
            frontmatter.get("version") or customize_data.get("version") or parsed_uri.version_or_ref
        )
        raw_policy = str(
            customize_data.get("adaptive_gate_policy")
            or scalars_dict.get("adaptive_gate_policy")
            or "STANDARD"
        ).upper()
        gate_policy: AdaptiveGatePolicy = (
            cast(AdaptiveGatePolicy, raw_policy)
            if raw_policy in ("STRICT", "STANDARD", "LENIENT")
            else "STANDARD"
        )

        provisional_wf = WorkflowDefinitionEntity(
            id=new_uuid7_str(),
            workspace_id=pack.workspace_id,
            uri=parsed_uri.raw_uri,
            title=frontmatter["name"],
            description=frontmatter["description"],
            version=version,
            source_format="BMAD_PACK",
            adaptive_gate_policy=gate_policy,
            scalars=scalars,
            datasources=(parsed_uri.raw_uri, *_str_tuple("datasources")),
            rules=_str_tuple("rules"),
            facts=_str_tuple("facts"),
            lenses=lenses,
            steps=steps,
            sha256="",
            customize_metadata=customize_data,
        )
        wf_sha256 = compute_workflow_sha256(provisional_wf)
        workflow_def = replace(provisional_wf, sha256=wf_sha256)

        pack_bundle_json = json.dumps(
            {
                "uri": parsed_uri.raw_uri,
                "source_format": "BMAD_PACK",
                "skill_markdown": pack.skill_markdown,
                "customize_toml": pack.customize_toml,
                "steps": [
                    {"filename": s.filename, "content_markdown": s.content_markdown}
                    for s in sorted_step_files
                ],
                "workflow_sha256": wf_sha256,
            },
            sort_keys=True,
        )
        bundle_sha256 = compute_bytes_sha256(pack_bundle_json.encode("utf-8"))
        if resolver is not None:
            resolver.register_upstream_payload(
                parsed_uri.raw_uri, pack_bundle_json, resolved_version=version, prewarm_cas=True
            )

        catalog_item = CatalogItemEntity(
            id=new_uuid7_str(),
            resource_id=f"bmad-{slug}",
            uri=parsed_uri.raw_uri,
            scheme=parsed_uri.scheme,
            title=frontmatter["name"],
            description=frontmatter["description"],
            resource_type="skill",
            source_format="BMAD_PACK",
            version=version,
            sha256=bundle_sha256,
            cas_key=f"cas/{bundle_sha256}",
            visibility_scope="SHARED_WORKSPACE" if pack.workspace_id else "SHARED_TEAM",
            owner_org_unit_id=pack.owner_org_unit_id,
            owner_workspace_id=pack.workspace_id,
            content_payload=pack_bundle_json,
        )
        return catalog_item, workflow_def

    @classmethod
    def import_from_archive_bytes(
        cls,
        *,
        uri: str,
        archive_bytes: bytes,
        workspace_id: str | None = None,
        owner_org_unit_id: str = "0192c4e0-0000-7000-8000-000000000104",
        resolver: FederatedUriResolver | None = None,
    ) -> tuple[CatalogItemEntity, WorkflowDefinitionEntity]:
        """Extract `SKILL.md`, `customize.toml`, and `steps/*.md` from `.tar.gz` or `.zip` bytes."""
        parsed = parse_federated_uri(uri)
        files_map: dict[str, str] = {}
        try:
            if parsed.archive_format == "zip":
                with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
                    for name in zf.namelist():
                        norm = name.strip("/")
                        if not name.endswith("/") and _is_bmad_archive_entry(norm):
                            files_map[norm] = zf.read(name).decode("utf-8")
            else:
                with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:*") as tf:
                    for member in tf.getmembers():
                        norm = member.name.strip("/")
                        if member.isfile() and _is_bmad_archive_entry(norm):
                            extracted = tf.extractfile(member)
                            if extracted is not None:
                                files_map[norm] = extracted.read().decode("utf-8")
        except (tarfile.TarError, zipfile.BadZipFile, UnicodeDecodeError) as exc:
            raise ValidationDomainError(
                detail_override=f"Corrupted BMAD archive for {uri}: {exc}"
            ) from exc

        skill_md, customize_toml = "", ""
        step_files: list[BmadSkillStepFile] = []
        for norm, text in files_map.items():
            if norm == "SKILL.md" or norm.endswith("/SKILL.md"):
                skill_md = text
            elif norm == "customize.toml" or norm.endswith("/customize.toml"):
                customize_toml = text
            elif "/steps/" in f"/{norm}" and norm.endswith(".md"):
                step_files.append(
                    BmadSkillStepFile(filename=norm.rsplit("/", 1)[-1], content_markdown=text)
                )
        return cls.import_pack(
            BmadSkillPackInput(
                uri=uri,
                skill_markdown=skill_md,
                customize_toml=customize_toml,
                steps=tuple(step_files),
                workspace_id=workspace_id,
                owner_org_unit_id=owner_org_unit_id,
            ),
            resolver=resolver,
        )
