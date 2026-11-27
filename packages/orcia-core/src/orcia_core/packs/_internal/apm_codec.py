"""Native APM-Superset & legacy `pack.yaml` archive codec (`Story 31.1`, `D3`, `D4`)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from orcia_core.gates import StarlarkMechanismSandbox, StarlarkSandboxError
from orcia_core.packs._internal._apm_bundle_synthesizer import synthesize_files_from_bundle
from orcia_core.packs._internal._apm_entry_router import ParsedPackEntries, ingest_pack_entry
from orcia_core.packs._internal._apm_manifest_parser import (
    build_lockfile_dict,
    compute_archive_sha256,
    parse_manifest,
    strip_single_root_folder,
    verify_lockfile,
)
from orcia_core.packs._internal._apm_markdown_parser import parse_starlark_mechanism
from orcia_core.packs._internal._apm_security_guards import (
    MAX_ARCHIVE_COMPRESSED_BYTES,
    MAX_ARCHIVE_FILES,
    MAX_COMPRESSION_RATIO,
    MAX_SINGLE_FILE_BYTES,
    MAX_UNCOMPRESSED_BYTES,
    assert_no_executable_hooks_or_scripts,
    assert_no_executable_magic_bytes,
    normalize_and_validate_archive_path,
    validate_zip_info_safe,
)
from orcia_core.packs.errors import PackInvalidArchiveError
from orcia_core.packs.models import (
    LoadedPackBundleV2,
    PackBundleKind,
    PackDnaMechanismSpec,
    PackScopeType,
    PackSourceOrigin,
)

_DETERMINISTIC_ZIP_DT = (2026, 1, 1, 0, 0, 0)


class ApmPackCodec:
    """Pure Python codec for APM-Superset & legacy declarative pack bundles."""

    def __init__(self, *, starlark_sandbox: StarlarkMechanismSandbox | None = None) -> None:
        self._sandbox = starlark_sandbox or StarlarkMechanismSandbox()

    def decode_directory(
        self,
        pack_dir: Path,
        *,
        source_origin: PackSourceOrigin = PackSourceOrigin.LOCAL_SYSTEM,
    ) -> LoadedPackBundleV2:
        """Decode and validate an on-disk APM or legacy pack directory."""
        if not pack_dir.exists() or not pack_dir.is_dir():
            raise PackInvalidArchiveError(
                detail_override=f"Pack directory does not exist: {str(pack_dir)!r}"
            )
        files: dict[str, bytes] = {}
        total_bytes = 0
        for item in sorted(pack_dir.rglob("*")):
            if item.is_symlink():
                raise PackInvalidArchiveError(
                    detail_override=f"Symbolic link is forbidden inside pack: {str(item)!r}"
                )
            if not item.is_file():
                continue
            rel = normalize_and_validate_archive_path(item.relative_to(pack_dir).as_posix())
            assert_no_executable_hooks_or_scripts(rel)
            if len(files) >= MAX_ARCHIVE_FILES:
                raise PackInvalidArchiveError(
                    detail_override=f"Pack directory exceeds {MAX_ARCHIVE_FILES} entries limit."
                )
            file_size = item.stat().st_size
            if file_size > MAX_SINGLE_FILE_BYTES:
                raise PackInvalidArchiveError(
                    detail_override=(
                        f"Pack file {rel!r} exceeds {MAX_SINGLE_FILE_BYTES} bytes limit."
                    )
                )
            total_bytes += file_size
            if total_bytes > MAX_UNCOMPRESSED_BYTES:
                raise PackInvalidArchiveError(detail_override="Pack directory exceeds size limits.")
            blob = item.read_bytes()
            assert_no_executable_magic_bytes(blob, rel_path=rel)
            files[rel] = blob
        return self._decode_file_map(files, source_origin=source_origin)

    def decode_zip_bytes(
        self,
        zip_bytes: bytes,
        *,
        source_origin: PackSourceOrigin = PackSourceOrigin.APM_ZIP,
        allow_system_kind: bool = False,
    ) -> LoadedPackBundleV2:
        """Decode and validate an in-memory `.zip` archive fail-closed."""
        if not zip_bytes or len(zip_bytes) > MAX_ARCHIVE_COMPRESSED_BYTES:
            raise PackInvalidArchiveError(
                detail_override="ZIP archive is empty or exceeds maximum compressed size."
            )
        files: dict[str, bytes] = {}
        total_uncompressed = 0
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes), mode="r") as zf:
                infos = zf.infolist()
                if len(infos) > MAX_ARCHIVE_FILES:
                    raise PackInvalidArchiveError(
                        detail_override=f"Archive exceeds {MAX_ARCHIVE_FILES} entries limit."
                    )
                for info in infos:
                    if info.is_dir():
                        continue
                    rel = validate_zip_info_safe(info)
                    assert_no_executable_hooks_or_scripts(rel)
                    with zf.open(info, "r") as handle:
                        blob = handle.read(MAX_SINGLE_FILE_BYTES + 1)
                    if len(blob) > MAX_SINGLE_FILE_BYTES:
                        raise PackInvalidArchiveError(
                            detail_override=f"Decompressed entry {rel!r} exceeds size limit."
                        )
                    if (
                        info.compress_size > 0
                        and (len(blob) / info.compress_size) > MAX_COMPRESSION_RATIO
                    ):
                        raise PackInvalidArchiveError(
                            detail_override=f"Decompressed entry {rel!r} exceeds ratio limit."
                        )
                    total_uncompressed += len(blob)
                    if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                        raise PackInvalidArchiveError(
                            detail_override="Total uncompressed archive size exceeds safety limit."
                        )
                    assert_no_executable_magic_bytes(blob, rel_path=rel)
                    files[rel] = blob
        except zipfile.BadZipFile as exc:
            raise PackInvalidArchiveError(detail_override=f"Corrupted ZIP archive: {exc}") from exc
        stripped = strip_single_root_folder(files)
        bundle = self._decode_file_map(stripped, source_origin=source_origin)
        if not allow_system_kind and (
            bundle.manifest.bundle_kind == PackBundleKind.SYSTEM
            or bundle.manifest.scope_type == PackScopeType.GLOBAL
        ):
            raise PackInvalidArchiveError(
                detail_override=(
                    "Uploaded ZIP archives cannot declare SYSTEM bundle_kind or GLOBAL scope_type."
                )
            )
        return bundle

    def encode_zip_bytes(self, bundle: LoadedPackBundleV2) -> bytes:
        """Serialize a `LoadedPackBundleV2` into deterministic, reproducible `.zip` bytes."""
        buf = io.BytesIO()
        prefix = bundle.manifest.slug.strip("/")
        files_to_write = (
            dict(bundle.raw_files) if bundle.raw_files else synthesize_files_from_bundle(bundle)
        )
        if (
            "apm.yml" not in files_to_write
            and "pack.yaml" not in files_to_write
            and bundle.manifest_yaml
        ):
            files_to_write["apm.yml"] = bundle.manifest_yaml.encode("utf-8")
        if "apm.lock.yaml" not in files_to_write and "apm.yml" in files_to_write:
            lock_yaml = yaml.safe_dump(
                build_lockfile_dict(files_to_write), allow_unicode=True, sort_keys=True
            )
            files_to_write["apm.lock.yaml"] = lock_yaml.encode("utf-8")

        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for rel_path in sorted(files_to_write.keys()):
                arcname = f"{prefix}/{rel_path}" if prefix else rel_path
                zinfo = zipfile.ZipInfo(filename=arcname, date_time=_DETERMINISTIC_ZIP_DT)
                zinfo.compress_type = zipfile.ZIP_DEFLATED
                zinfo.external_attr = 0o644 << 16
                zf.writestr(zinfo, files_to_write[rel_path])
        return buf.getvalue()

    def _decode_file_map(
        self,
        files: dict[str, bytes],
        *,
        source_origin: PackSourceOrigin,
    ) -> LoadedPackBundleV2:
        try:
            manifest, manifest_yaml = parse_manifest(files, source_origin=source_origin)
            lockfile = verify_lockfile(files)
        except (ValidationError, ValueError, TypeError) as exc:
            raise PackInvalidArchiveError(
                detail_override=f"Pack manifest schema validation failed: {exc}"
            ) from exc

        acc = ParsedPackEntries()
        for rel_path in sorted(files.keys()):
            try:
                ingest_pack_entry(acc, rel_path=rel_path, blob=files[rel_path])
            except (UnicodeDecodeError, ValidationError, ValueError, TypeError) as exc:
                raise PackInvalidArchiveError(
                    detail_override=f"Invalid pack entry {rel_path!r}: {exc}"
                ) from exc

        dna_mechanisms = self._validate_starlark_mechanisms(acc.star_sources, acc.star_meta)
        provisional = LoadedPackBundleV2(
            manifest=manifest,
            archive_sha256="0" * 64,
            manifest_yaml=manifest_yaml,
            lockfile=lockfile,
            agents=acc.agents,
            skills=acc.skills,
            instructions=acc.instructions,
            vsm_specs=acc.vsm_specs,
            workflows=acc.workflows,
            glossary=acc.glossary,
            dna_mechanisms=dna_mechanisms,
            gates_specs=acc.gates_specs,
            policies=acc.policies,
            help_articles=acc.help_articles,
            raw_files=files,
        )
        canonical_zip = self.encode_zip_bytes(provisional)
        return provisional.model_copy(
            update={"archive_sha256": compute_archive_sha256(canonical_zip)}
        )

    def _validate_starlark_mechanisms(
        self,
        star_sources: dict[str, str],
        star_meta: dict[str, dict[str, Any]],
    ) -> list[PackDnaMechanismSpec]:
        mechanisms: list[PackDnaMechanismSpec] = []
        for stem in sorted(star_sources.keys()):
            spec = parse_starlark_mechanism(stem, star_sources[stem], star_meta.get(stem))
            try:
                if spec.passing_test_payload is not None:
                    res = self._sandbox.evaluate_script(
                        starlark_code=spec.starlark_source, payload=spec.passing_test_payload
                    )
                    if not res.passed:
                        raise PackInvalidArchiveError(
                            detail_override=(
                                f"Starlark mechanism {stem!r} failed passing_test_payload."
                            )
                        )
                if spec.failing_test_payload is not None:
                    res = self._sandbox.evaluate_script(
                        starlark_code=spec.starlark_source, payload=spec.failing_test_payload
                    )
                    if res.passed:
                        raise PackInvalidArchiveError(
                            detail_override=(
                                f"Starlark mechanism {stem!r} passed failing_test_payload."
                            )
                        )
            except StarlarkSandboxError as exc:
                raise PackInvalidArchiveError(
                    detail_override=f"Starlark mechanism {stem!r} sandbox error: {exc}"
                ) from exc
            mechanisms.append(spec)
        return mechanisms


__all__ = ["ApmPackCodec", "build_lockfile_dict", "compute_archive_sha256"]
