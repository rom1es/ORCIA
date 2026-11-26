import {
  extractDraftPackReferences,
  extractMissingClosureDependencies,
  extractMissingSlotsFromProblem,
  extractPackLeakFindings,
  OrciaProblemError,
  type PackDraftDetailResponse,
  type WorkspacePackItemResponse,
} from "@orcia/api-client";
import type {
  ControlCenterDatasourceItem,
  UiDraftPackReference,
  UiPackComposerEntityType,
  UiPackDraftItem,
  UiPackSlotTargetCandidate,
  UiWorkspacePackItem,
} from "@orcia/ui";
import type { SupportedWebLocale } from "../../../i18n";
import { formatRfc9457ErrorToBanner } from "../../../lib/formatRfc9457ErrorToBanner";

export function mapWorkspacePackDtoToUi(dto: WorkspacePackItemResponse): UiWorkspacePackItem {
  return {
    bundleId: dto.bundle_id,
    packId: dto.pack_id,
    slug: dto.slug,
    name: dto.name,
    version: dto.version,
    bundleKind: dto.bundle_kind,
    scopeType: dto.scope_type,
    scopeId: dto.scope_id,
    status: dto.status,
    archiveSha256: dto.archive_sha256,
    description: dto.description ?? "",
    isActive: Boolean(dto.is_active),
    priorityOrder: dto.priority_order ?? null,
    declaredSlots: (dto.declared_slots ?? []).map((s) => ({
      slotKey: s.slot_key,
      scheme: s.scheme,
      connectorKind: s.connector_kind ?? "",
      sourceNature: s.source_nature ?? "",
      required: s.required !== false,
      description: s.description_fr || s.description_en || s.slot_key,
    })),
    slotBindings: (dto.slot_bindings ?? []).map((b) => ({
      slotKey: b.slot_key,
      targetKind: b.target_kind,
      targetId: b.target_id ?? null,
      targetDisplayName: b.target_display_name ?? null,
      targetUri: b.target_uri ?? null,
      targetEnabled: b.target_enabled !== false,
      isEffectiveBound: Boolean(b.is_effective_bound),
    })),
    missingSlots: dto.missing_slots ?? [],
    readinessOk: dto.readiness_ok !== false,
  };
}

export function mapPackDraftDtoToUi(dto: PackDraftDetailResponse): UiPackDraftItem {
  return {
    bundleId: dto.bundle_id,
    slug: dto.slug,
    name: dto.name,
    version: dto.version,
    description: dto.description ?? "",
    author: dto.author ?? "",
    license: dto.license ?? "",
    scopeType:
      dto.scope_type === "BU" || dto.scope_type === "TEAM" ? dto.scope_type : "WORKSPACE",
    scopeId: dto.scope_id ?? "",
    status: dto.status ?? "DRAFT",
    members: (dto.members ?? []).map((m) => ({
      entityType: m.entity_type as UiPackComposerEntityType,
      entityId: m.entity_id,
      entitySlug: m.entity_slug,
      title: m.title || m.entity_slug,
      lifecycleStatus: m.lifecycle_status ?? "ACTIVE",
    })),
    closureComplete: dto.closure?.complete ?? true,
    missingDependencies: (dto.closure?.missing_dependencies ?? []).map((d) => ({
      entityType: d.entity_type,
      entityId: d.entity_id,
      reason: d.reason,
      referencedBy: d.referenced_by,
    })),
    nonActiveDependencies: (dto.closure?.non_active_dependencies ?? []).map((d) => ({
      entityType: d.entity_type,
      entityId: d.entity_id,
      reason: d.reason,
      referencedBy: d.referenced_by,
    })),
    proseWarnings: (dto.closure?.prose_lint_warnings ?? []).map((w) => ({
      entityType: w.entity_type,
      entitySlug: w.entity_slug,
      token: w.token,
      message: w.message,
    })),
  };
}

export function mapDatasourcesToSlotCandidates(
  datasources: readonly ControlCenterDatasourceItem[],
  workspaceName?: string,
): readonly UiPackSlotTargetCandidate[] {
  return datasources
    .filter((ds) => !workspaceName || !ds.workspaceName || ds.workspaceName === workspaceName)
    .map((ds) => ({
      targetKind: "WORKSPACE_DATASOURCE" as const,
      targetId: ds.id,
      label: ds.alias,
      scheme: ds.scheme,
      uri: ds.uri,
    }));
}

export function formatDetailedPackError(
  err: unknown,
  locale: SupportedWebLocale,
  contextLabel?: string,
): {
  readonly fullText: string;
  readonly errorCode?: string;
  readonly missingSlots: readonly string[];
  readonly draftPacks: readonly UiDraftPackReference[];
} {
  const banner = formatRfc9457ErrorToBanner(err, locale, contextLabel);
  const missingSlots = extractMissingSlotsFromProblem(err);
  const missingDeps = extractMissingClosureDependencies(err);
  const leakFindings = extractPackLeakFindings(err);
  const draftPacks = extractDraftPackReferences(err);

  const extraParts: string[] = [];
  if (missingSlots.length > 0) {
    extraParts.push(missingSlots.join(", "));
  }
  if (missingDeps.length > 0) {
    extraParts.push(missingDeps.map((d) => `${d.entityType}:${d.entityId}`).join(", "));
  }
  if (leakFindings.length > 0) {
    extraParts.push(leakFindings.map((l) => `${l.path} (${l.kind})`).join(", "));
  }
  const code =
    err instanceof OrciaProblemError ? err.problem.error_code : banner.errorCode;
  const codeSuffix = code ? ` [${code}]` : "";
  const extraSuffix = extraParts.length > 0 ? ` — ${extraParts.join(" ; ")}` : "";
  return {
    fullText: `${banner.fullText}${extraSuffix}${codeSuffix}`,
    errorCode: code,
    missingSlots,
    draftPacks,
  };
}

export function triggerBrowserZipDownload(blob: Blob, filename: string): void {
  if (typeof URL === "undefined" || typeof URL.createObjectURL !== "function") return;
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(objectUrl);
}
