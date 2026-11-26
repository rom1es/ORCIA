import { createOrciaApiClient } from "@orcia/api-client";
import type {
  PackComposerSavePayload,
  UiPackComposerEntityType,
  UiPackDraftItem,
  UiPackDraftMemberOption,
} from "@orcia/ui";
import { useCallback, useEffect, useMemo, useState } from "react";
import { formatI18nTemplate, useI18n } from "../../../i18n";
import { useAuthSessionStore } from "../../../stores/authSessionStore";
import {
  formatDetailedPackError,
  mapPackDraftDtoToUi,
  triggerBrowserZipDownload,
} from "./packMappers";
import { usePackImportAndUninstallController } from "./usePackImportAndUninstallController";

export function usePackComposerAndImportController(params: {
  readonly activeWorkspaceId: string;
  readonly onPacksMutated: () => Promise<void> | void;
  readonly onStatusMessage: (msg: string) => void;
  readonly onErrorMessage: (msg: string) => void;
}) {
  const { activeWorkspaceId, onPacksMutated, onStatusMessage, onErrorMessage } = params;
  const { dictionary, locale } = useI18n();
  const actionsCopy = dictionary.packsUi.actions;
  const accessToken = useAuthSessionStore((s) => s.accessToken);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "", locale }), [locale]);

  const [drafts, setDrafts] = useState<readonly UiPackDraftItem[]>([]);
  const [composerOpen, setComposerOpen] = useState(false);
  const [activeDraft, setActiveDraft] = useState<UiPackDraftItem | null>(null);
  const [availableMembers, setAvailableMembers] = useState<readonly UiPackDraftMemberOption[]>([]);
  const [isComposerBusy, setIsComposerBusy] = useState(false);
  const [composerError, setComposerError] = useState<string | null>(null);

  const loadDrafts = useCallback(async () => {
    try {
      const res = await apiClient.listPackDrafts({ status: "ALL" });
      setDrafts((res.drafts ?? []).map(mapPackDraftDtoToUi));
    } catch (err: unknown) {
      onErrorMessage(formatDetailedPackError(err, locale).fullText);
    }
  }, [apiClient, locale, onErrorMessage]);

  useEffect(() => {
    void loadDrafts();
  }, [accessToken, loadDrafts]);

  const importCtrl = usePackImportAndUninstallController({
    onRefreshAll: async () => {
      await Promise.all([Promise.resolve(onPacksMutated()), loadDrafts()]);
    },
    onStatusMessage,
    onErrorMessage,
  });

  const loadComposerMembers = useCallback(async () => {
    try {
      const [agentsRes, wfRes, vsmRes] = await Promise.all([
        apiClient.listAgentsAndSkills(undefined, activeWorkspaceId || undefined),
        apiClient.listWorkflowsV2(),
        apiClient.listValueStreamMaps(),
      ]);
      const memberOptions: UiPackDraftMemberOption[] = [
        ...(agentsRes.agents ?? [])
          .filter((a) => a.visibility_scope !== "PACK")
          .map((a) => ({
            entityType: "AGENT" as UiPackComposerEntityType,
            entityId: a.agent_id,
            entitySlug: a.slug,
            title: a.name,
            lifecycleStatus: a.lifecycle_status ?? "ACTIVE",
          })),
        ...(agentsRes.skills ?? [])
          .filter((s) => s.visibility_scope !== "PACK")
          .map((s) => ({
            entityType: "SKILL" as UiPackComposerEntityType,
            entityId: s.skill_id,
            entitySlug: s.slug,
            title: s.name,
            lifecycleStatus: "ACTIVE",
          })),
        ...(wfRes.items ?? []).map((w) => ({
          entityType: "WORKFLOW_V2" as UiPackComposerEntityType,
          entityId: w.id,
          entitySlug: w.slug,
          title: w.title,
          lifecycleStatus: w.status === "published" ? "ACTIVE" : "DRAFT",
        })),
        ...(vsmRes.items ?? []).map((v) => ({
          entityType: "VSM_V2" as UiPackComposerEntityType,
          entityId: v.id,
          entitySlug: v.slug,
          title: v.title,
          lifecycleStatus: "ACTIVE",
        })),
      ];
      setAvailableMembers(memberOptions);
    } catch (err: unknown) {
      setComposerError(formatDetailedPackError(err, locale).fullText);
    }
  }, [activeWorkspaceId, apiClient, locale]);

  const openCreateComposer = useCallback(() => {
    setActiveDraft(null);
    setComposerError(null);
    setComposerOpen(true);
    void loadComposerMembers();
  }, [loadComposerMembers]);

  const openEditComposer = useCallback(
    async (draftId: string) => {
      setComposerError(null);
      setComposerOpen(true);
      setIsComposerBusy(true);
      try {
        await loadComposerMembers();
        const detail = await apiClient.getPackDraft(draftId);
        setActiveDraft(mapPackDraftDtoToUi(detail));
      } catch (err: unknown) {
        setComposerError(formatDetailedPackError(err, locale).fullText);
      } finally {
        setIsComposerBusy(false);
      }
    },
    [apiClient, loadComposerMembers, locale],
  );

  const handleSaveDraft = useCallback(
    async (payload: PackComposerSavePayload) => {
      if (readOnlyObserver) return;
      setIsComposerBusy(true);
      setComposerError(null);
      try {
        const saved = payload.bundleId
          ? await apiClient.updatePackDraft(payload.bundleId, {
              name: payload.name,
              version: payload.version,
              description: payload.description,
              author: payload.author,
              license: payload.license,
            })
          : await apiClient.createPackDraft({
              slug: payload.slug,
              name: payload.name,
              version: payload.version,
              description: payload.description,
              author: payload.author,
              license: payload.license,
              scope_type: payload.scopeType,
              scope_id: payload.scopeId,
            });
        const withMembers = await apiClient.setPackDraftMembers(saved.bundle_id, {
          members: payload.members.map((m) => ({
            entity_type: m.entityType,
            entity_id: m.entityId,
            entity_slug: m.entitySlug,
          })),
        });
        setActiveDraft(mapPackDraftDtoToUi(withMembers));
        onStatusMessage(
          formatI18nTemplate(actionsCopy.draftSavedTemplate, { name: withMembers.name }),
        );
        await loadDrafts();
      } catch (err: unknown) {
        setComposerError(formatDetailedPackError(err, locale, payload.name).fullText);
      } finally {
        setIsComposerBusy(false);
      }
    },
    [actionsCopy.draftSavedTemplate, apiClient, loadDrafts, locale, onStatusMessage, readOnlyObserver],
  );

  const handlePublishDraft = useCallback(
    async (draftId: string, autoIncludeDependencies: boolean) => {
      if (readOnlyObserver) return;
      setIsComposerBusy(true);
      setComposerError(null);
      try {
        const published = await apiClient.publishPackDraft(draftId, {
          auto_include_dependencies: autoIncludeDependencies,
        });
        setActiveDraft(mapPackDraftDtoToUi(published));
        onStatusMessage(
          formatI18nTemplate(actionsCopy.draftPublishedTemplate, { name: published.name }),
        );
        await Promise.all([Promise.resolve(onPacksMutated()), loadDrafts()]);
      } catch (err: unknown) {
        setComposerError(formatDetailedPackError(err, locale).fullText);
      } finally {
        setIsComposerBusy(false);
      }
    },
    [actionsCopy.draftPublishedTemplate, apiClient, loadDrafts, locale, onPacksMutated, onStatusMessage, readOnlyObserver],
  );

  const handleExportDraftZip = useCallback(
    async (draftId: string, autoIncludeDependencies: boolean) => {
      if (readOnlyObserver) return;
      setIsComposerBusy(true);
      setComposerError(null);
      try {
        const result = await apiClient.exportPackDraftZip(draftId, {
          auto_include_dependencies: autoIncludeDependencies,
        });
        triggerBrowserZipDownload(result.blob, result.filename ?? `${draftId}.zip`);
      } catch (err: unknown) {
        setComposerError(formatDetailedPackError(err, locale).fullText);
      } finally {
        setIsComposerBusy(false);
      }
    },
    [apiClient, locale, readOnlyObserver],
  );

  const handleDeleteDraft = useCallback(
    async (draftId: string, slug: string) => {
      if (readOnlyObserver) return;
      try {
        await apiClient.deletePackDraft(draftId);
        onStatusMessage(formatI18nTemplate(actionsCopy.draftDeletedTemplate, { slug }));
        await loadDrafts();
      } catch (err: unknown) {
        onErrorMessage(formatDetailedPackError(err, locale, slug).fullText);
      }
    },
    [actionsCopy.draftDeletedTemplate, apiClient, loadDrafts, locale, onErrorMessage, onStatusMessage, readOnlyObserver],
  );

  return {
    ...importCtrl,
    drafts,
    composerOpen,
    setComposerOpen,
    activeDraft,
    availableMembers,
    isComposerBusy,
    composerError,
    openCreateComposer,
    openEditComposer,
    handleSaveDraft,
    handlePublishDraft,
    handleExportDraftZip,
    handleDeleteDraft,
  };
}
