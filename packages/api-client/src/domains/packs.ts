import type {
  ActivateWorkspacePackRequest,
  ActivateWorkspacePackResponse,
  BindWorkspacePackSlotsRequest,
  BindWorkspacePackSlotsResponse,
  CreatePackDraftRequest,
  DeactivateWorkspacePackResponse,
  PackDeleteResponse,
  PackDraftDeleteResponse,
  PackDraftDetailResponse,
  PackDraftListResponse,
  PackExportRequest,
  PackImportRequest,
  PackImportResponse,
  PackPublishRequest,
  ReorderWorkspacePacksRequest,
  ReorderWorkspacePacksResponse,
  RunLockManifestReadResponse,
  SetPackDraftMembersRequest,
  UpdatePackDraftRequest,
  WorkspacePacksListResponse,
} from "../generated/packs";
import type {
  DeclarativePacksListResponse,
  PacksConnectorHealthResponse,
} from "../generated/process_studio_v2";
import {
  buildPersonaQuery,
  OrciaClientError,
  type BinaryDownloadResult,
  type createRequestBinary,
  type createRequestJson,
} from "../helpers";
import type { createRequestMultipart } from "../multipartHelper";

type RequestJsonFn = ReturnType<typeof createRequestJson>;
type RequestBinaryFn = ReturnType<typeof createRequestBinary>;
type RequestMultipartFn = ReturnType<typeof createRequestMultipart>;

export interface ImportPackFileInput {
  readonly file: File | Blob;
  readonly filename?: string;
  readonly scopeType?: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
  readonly scopeId?: string;
  readonly replaceDraft?: boolean;
}

export interface ListPackDraftsParams {
  readonly scopeType?: "BU" | "TEAM" | "WORKSPACE";
  readonly scopeId?: string;
  readonly status?: "DRAFT" | "PUBLISHED" | "DEPRECATED" | "ALL";
  readonly personaKey?: string;
}

export interface PackExportOptions extends PackExportRequest {
  readonly personaKey?: string;
}

export interface PackPublishOptions extends PackPublishRequest {
  readonly personaKey?: string;
}

function buildOptionsQuery(params: {
  readonly autoIncludeDependencies?: boolean;
  readonly personaKey?: string;
}): string {
  const qs = new URLSearchParams();
  if (params.autoIncludeDependencies) {
    qs.set("auto_include_dependencies", "true");
  }
  if (params.personaKey) {
    qs.set("persona_key", params.personaKey);
  }
  const encoded = qs.toString();
  return encoded ? `?${encoded}` : "";
}

export function createPacksDomainClient(
  requestJson: RequestJsonFn,
  requestBinary?: RequestBinaryFn,
  requestMultipart?: RequestMultipartFn,
) {
  const requireBinary = (): RequestBinaryFn => {
    if (!requestBinary) {
      throw new OrciaClientError("ERR_CLIENT_NOT_CONFIGURED", {
        detail: "packs.requestBinary",
      });
    }
    return requestBinary;
  };

  const requireMultipart = (): RequestMultipartFn => {
    if (!requestMultipart) {
      throw new OrciaClientError("ERR_CLIENT_NOT_CONFIGURED", {
        detail: "packs.requestMultipart",
      });
    }
    return requestMultipart;
  };

  return {
    listDeclarativePacks(): Promise<DeclarativePacksListResponse> {
      return requestJson<DeclarativePacksListResponse>("/api/v1/packs");
    },
    getPacksHealth(): Promise<PacksConnectorHealthResponse> {
      return requestJson<PacksConnectorHealthResponse>("/api/v1/packs/health");
    },
    importPackArchive(payload: PackImportRequest): Promise<PackImportResponse> {
      return requestJson<PackImportResponse>("/api/v1/packs/import", "POST", payload);
    },
    importPackArchiveFile(input: ImportPackFileInput): Promise<PackImportResponse> {
      const formData = new FormData();
      formData.append("file", input.file, input.filename ?? "pack.zip");
      if (input.scopeType) formData.append("scope_type", input.scopeType);
      if (input.scopeId) formData.append("scope_id", input.scopeId);
      if (input.replaceDraft !== undefined) {
        formData.append("replace_draft", String(input.replaceDraft));
      }
      return requireMultipart()<PackImportResponse>("/api/v1/packs/import", formData);
    },
    deletePackBundle(bundleId: string): Promise<PackDeleteResponse> {
      return requestJson<PackDeleteResponse>(
        `/api/v1/packs/${encodeURIComponent(bundleId)}`,
        "DELETE",
      );
    },
    exportPackBundleZip(
      bundleId: string,
      options: PackExportOptions = {},
    ): Promise<BinaryDownloadResult> {
      const q = buildOptionsQuery({
        autoIncludeDependencies: options.auto_include_dependencies,
        personaKey: options.personaKey,
      });
      return requireBinary()(
        `/api/v1/packs/${encodeURIComponent(bundleId)}/export${q}`,
        "POST",
      );
    },
    listWorkspacePacks(
      workspaceId: string,
      personaKey?: string,
    ): Promise<WorkspacePacksListResponse> {
      return requestJson<WorkspacePacksListResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/packs${buildPersonaQuery(personaKey)}`,
      );
    },
    activateWorkspacePack(
      workspaceId: string,
      slug: string,
      payload?: ActivateWorkspacePackRequest,
      personaKey?: string,
    ): Promise<ActivateWorkspacePackResponse> {
      return requestJson<ActivateWorkspacePackResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/packs/${encodeURIComponent(slug)}/activate${buildPersonaQuery(personaKey)}`,
        "POST",
        payload ?? {},
      );
    },
    deactivateWorkspacePack(
      workspaceId: string,
      slug: string,
      personaKey?: string,
    ): Promise<DeactivateWorkspacePackResponse> {
      return requestJson<DeactivateWorkspacePackResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/packs/${encodeURIComponent(slug)}/deactivate${buildPersonaQuery(personaKey)}`,
        "DELETE",
      );
    },
    reorderWorkspacePacks(
      workspaceId: string,
      payload: ReorderWorkspacePacksRequest,
      personaKey?: string,
    ): Promise<ReorderWorkspacePacksResponse> {
      return requestJson<ReorderWorkspacePacksResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/packs/reorder${buildPersonaQuery(personaKey)}`,
        "PUT",
        payload,
      );
    },
    bindWorkspacePackSlots(
      workspaceId: string,
      slug: string,
      payload: BindWorkspacePackSlotsRequest,
      personaKey?: string,
    ): Promise<BindWorkspacePackSlotsResponse> {
      return requestJson<BindWorkspacePackSlotsResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/packs/${encodeURIComponent(slug)}/slots${buildPersonaQuery(personaKey)}`,
        "PUT",
        payload,
      );
    },
    getWorkflowV2RunLock(
      runId: string,
      personaKey?: string,
    ): Promise<RunLockManifestReadResponse> {
      return requestJson<RunLockManifestReadResponse>(
        `/api/v1/runs/${encodeURIComponent(runId)}/lock${buildPersonaQuery(personaKey)}`,
      );
    },
    listPackDrafts(params: ListPackDraftsParams = {}): Promise<PackDraftListResponse> {
      const qs = new URLSearchParams();
      if (params.scopeType) qs.set("scope_type", params.scopeType);
      if (params.scopeId) qs.set("scope_id", params.scopeId);
      if (params.status) qs.set("status", params.status);
      if (params.personaKey) qs.set("persona_key", params.personaKey);
      const q = qs.toString();
      return requestJson<PackDraftListResponse>(
        `/api/v1/packs/composer${q ? `?${q}` : ""}`,
      );
    },
    createPackDraft(
      payload: CreatePackDraftRequest,
      personaKey?: string,
    ): Promise<PackDraftDetailResponse> {
      return requestJson<PackDraftDetailResponse>(
        `/api/v1/packs/composer${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    getPackDraft(draftId: string, personaKey?: string): Promise<PackDraftDetailResponse> {
      return requestJson<PackDraftDetailResponse>(
        `/api/v1/packs/composer/${encodeURIComponent(draftId)}${buildPersonaQuery(personaKey)}`,
      );
    },
    updatePackDraft(
      draftId: string,
      payload: UpdatePackDraftRequest,
      personaKey?: string,
    ): Promise<PackDraftDetailResponse> {
      return requestJson<PackDraftDetailResponse>(
        `/api/v1/packs/composer/${encodeURIComponent(draftId)}${buildPersonaQuery(personaKey)}`,
        "PATCH",
        payload,
      );
    },
    setPackDraftMembers(
      draftId: string,
      payload: SetPackDraftMembersRequest,
      personaKey?: string,
    ): Promise<PackDraftDetailResponse> {
      return requestJson<PackDraftDetailResponse>(
        `/api/v1/packs/composer/${encodeURIComponent(draftId)}/members${buildPersonaQuery(personaKey)}`,
        "PUT",
        payload,
      );
    },
    deletePackDraft(
      draftId: string,
      personaKey?: string,
    ): Promise<PackDraftDeleteResponse> {
      return requestJson<PackDraftDeleteResponse>(
        `/api/v1/packs/composer/${encodeURIComponent(draftId)}${buildPersonaQuery(personaKey)}`,
        "DELETE",
      );
    },
    publishPackDraft(
      draftId: string,
      options: PackPublishOptions = {},
    ): Promise<PackDraftDetailResponse> {
      const q = buildOptionsQuery({
        autoIncludeDependencies: options.auto_include_dependencies,
        personaKey: options.personaKey,
      });
      return requestJson<PackDraftDetailResponse>(
        `/api/v1/packs/composer/${encodeURIComponent(draftId)}/publish${q}`,
        "POST",
        { auto_include_dependencies: Boolean(options.auto_include_dependencies) },
      );
    },
    exportPackDraftZip(
      draftId: string,
      options: PackExportOptions = {},
    ): Promise<BinaryDownloadResult> {
      const q = buildOptionsQuery({
        autoIncludeDependencies: options.auto_include_dependencies,
        personaKey: options.personaKey,
      });
      return requireBinary()(
        `/api/v1/packs/composer/${encodeURIComponent(draftId)}/export${q}`,
        "POST",
      );
    },
  };
}
