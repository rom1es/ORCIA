import { createOrciaApiClient, type WorkspaceDatasourceItemResponse } from "@orcia/api-client";
import type {
  PackSlotBindingDraftEntry,
  UiWorkspacePackItem,
} from "@orcia/ui";
import { useCallback, useEffect, useMemo, useState } from "react";
import { formatI18nTemplate, useI18n } from "../../../i18n";
import { useAuthSessionStore } from "../../../stores/authSessionStore";
import { formatDetailedPackError, mapWorkspacePackDtoToUi } from "./packMappers";

export function useWorkspacePacksController(params: {
  readonly workspaceId: string;
  readonly onStatusMessage?: (message: string) => void;
}) {
  const { workspaceId, onStatusMessage } = params;
  const { dictionary, locale } = useI18n();
  const actionsCopy = dictionary.packsUi.actions;
  const accessToken = useAuthSessionStore((s) => s.accessToken);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "", locale }), [locale]);

  const [packs, setPacks] = useState<readonly UiWorkspacePackItem[]>([]);
  const [workspaceDatasources, setWorkspaceDatasources] = useState<
    readonly WorkspaceDatasourceItemResponse[]
  >([]);
  const [isLoading, setIsLoading] = useState(false);
  const [busySlug, setBusySlug] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [slotDrawerPack, setSlotDrawerPack] = useState<UiWorkspacePackItem | null>(null);
  const [slotDrawerMissingSlots, setSlotDrawerMissingSlots] = useState<readonly string[]>([]);
  const [slotDrawerError, setSlotDrawerError] = useState<string | null>(null);
  const [isSavingSlots, setIsSavingSlots] = useState(false);

  const loadWorkspacePacks = useCallback(async () => {
    if (!workspaceId) {
      setPacks([]);
      setWorkspaceDatasources([]);
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [packsResult, dsResult] = await Promise.allSettled([
        apiClient.listWorkspacePacks(workspaceId),
        apiClient.listWorkspaceDatasources(workspaceId),
      ]);
      if (packsResult.status === "rejected") {
        throw packsResult.reason;
      }
      setPacks((packsResult.value.packs ?? []).map(mapWorkspacePackDtoToUi));
      setWorkspaceDatasources(dsResult.status === "fulfilled" ? (dsResult.value.items ?? []) : []);
    } catch (err: unknown) {
      setErrorMessage(formatDetailedPackError(err, locale).fullText);
    } finally {
      setIsLoading(false);
    }
  }, [apiClient, locale, workspaceId]);

  useEffect(() => {
    void loadWorkspacePacks();
  }, [accessToken, loadWorkspacePacks]);

  const openSlotDrawer = useCallback((pack: UiWorkspacePackItem) => {
    setSlotDrawerPack(pack);
    setSlotDrawerMissingSlots(pack.missingSlots);
    setSlotDrawerError(null);
  }, []);

  const closeSlotDrawer = useCallback(() => {
    setSlotDrawerPack(null);
    setSlotDrawerMissingSlots([]);
    setSlotDrawerError(null);
  }, []);

  const handleToggleActivate = useCallback(
    async (pack: UiWorkspacePackItem) => {
      if (!workspaceId || readOnlyObserver) return;
      setBusySlug(pack.slug);
      setErrorMessage(null);
      try {
        if (pack.isActive) {
          await apiClient.deactivateWorkspacePack(workspaceId, pack.slug);
          onStatusMessage?.(
            formatI18nTemplate(actionsCopy.packDeactivatedSuccessTemplate, { slug: pack.slug }),
          );
        } else {
          await apiClient.activateWorkspacePack(workspaceId, pack.slug, {
            bundle_id: pack.bundleId,
          });
          onStatusMessage?.(
            formatI18nTemplate(actionsCopy.packActivatedSuccessTemplate, { slug: pack.slug }),
          );
        }
        await loadWorkspacePacks();
      } catch (err: unknown) {
        const parsed = formatDetailedPackError(err, locale, pack.name);
        setErrorMessage(parsed.fullText);
        if (parsed.errorCode === "ERR_PACK_SLOT_UNBOUND") {
          setSlotDrawerPack(pack);
          setSlotDrawerMissingSlots(
            parsed.missingSlots.length > 0 ? parsed.missingSlots : pack.missingSlots,
          );
          setSlotDrawerError(parsed.fullText);
        }
      } finally {
        setBusySlug(null);
      }
    },
    [
      actionsCopy.packActivatedSuccessTemplate,
      actionsCopy.packDeactivatedSuccessTemplate,
      apiClient,
      loadWorkspacePacks,
      locale,
      onStatusMessage,
      readOnlyObserver,
      workspaceId,
    ],
  );

  const handleMovePriority = useCallback(
    async (packSlug: string, direction: "up" | "down") => {
      if (!workspaceId || readOnlyObserver) return;
      const activeOrdered = packs
        .filter((p) => p.isActive)
        .sort((a, b) => (a.priorityOrder ?? 999) - (b.priorityOrder ?? 999))
        .map((p) => p.slug);
      const idx = activeOrdered.indexOf(packSlug);
      if (idx < 0) return;
      const swapIdx = direction === "up" ? idx - 1 : idx + 1;
      if (swapIdx < 0 || swapIdx >= activeOrdered.length) return;
      const reordered = [...activeOrdered];
      const current = reordered[idx]!;
      reordered[idx] = reordered[swapIdx]!;
      reordered[swapIdx] = current;

      setBusySlug(packSlug);
      setErrorMessage(null);
      try {
        await apiClient.reorderWorkspacePacks(workspaceId, {
          ordered_pack_slugs: reordered,
        });
        onStatusMessage?.(actionsCopy.packReorderedSuccess);
        await loadWorkspacePacks();
      } catch (err: unknown) {
        setErrorMessage(formatDetailedPackError(err, locale, packSlug).fullText);
      } finally {
        setBusySlug(null);
      }
    },
    [
      actionsCopy.packReorderedSuccess,
      apiClient,
      loadWorkspacePacks,
      locale,
      onStatusMessage,
      packs,
      readOnlyObserver,
      workspaceId,
    ],
  );

  const handleSaveSlotBindings = useCallback(
    async (pack: UiWorkspacePackItem, bindings: readonly PackSlotBindingDraftEntry[]) => {
      if (!workspaceId || readOnlyObserver) return;
      setIsSavingSlots(true);
      setSlotDrawerError(null);
      try {
        await apiClient.bindWorkspacePackSlots(workspaceId, pack.slug, {
          bundle_id: pack.bundleId,
          bindings: bindings.map((b) => ({
            slot_key: b.slotKey,
            target_kind: b.targetKind,
            target_id: b.targetId,
            connector_scheme: b.connectorScheme,
          })),
        });
        onStatusMessage?.(
          formatI18nTemplate(actionsCopy.slotBoundSuccessTemplate, { slug: pack.slug }),
        );
        closeSlotDrawer();
        await loadWorkspacePacks();
      } catch (err: unknown) {
        const parsed = formatDetailedPackError(err, locale, pack.name);
        setSlotDrawerError(parsed.fullText);
        if (parsed.missingSlots.length > 0) {
          setSlotDrawerMissingSlots(parsed.missingSlots);
        }
      } finally {
        setIsSavingSlots(false);
      }
    },
    [
      actionsCopy.slotBoundSuccessTemplate,
      apiClient,
      closeSlotDrawer,
      loadWorkspacePacks,
      locale,
      onStatusMessage,
      readOnlyObserver,
      workspaceId,
    ],
  );

  return {
    packs,
    workspaceDatasources,
    isLoading,
    busySlug,
    errorMessage,
    readOnlyObserver,
    slotDrawerPack,
    slotDrawerMissingSlots,
    slotDrawerError,
    isSavingSlots,
    reloadWorkspacePacks: loadWorkspacePacks,
    openSlotDrawer,
    closeSlotDrawer,
    handleToggleActivate,
    handleMovePriority,
    handleSaveSlotBindings,
  };
}
