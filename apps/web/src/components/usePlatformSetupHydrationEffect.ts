import { createOrciaApiClient } from "@orcia/api-client";
import { useEffect, useRef } from "react";
import { formatRfc9457ErrorToBanner } from "../lib/formatRfc9457ErrorToBanner";
import { resolveWebApiBaseUrl, useAuthSessionStore } from "../stores/authSessionStore";
import { EMPTY_CACHED_PLATFORM_SETUP_STATE } from "./platformSetupContextTypes";
import {
  buildAccostageCountsFromStatus,
  fetchAndBuildHydrationOutcome,
  savePlatformSetupSnapshotToApi,
  type AccostagePg18CountsView,
} from "./platformSetupHydration";
import {
  PLATFORM_SETUP_STATE_STORAGE_KEY,
  writeCachedPlatformSetupState,
  writeStorageItem,
  type CachedPlatformSetupState,
  type ConfiguredOrgUnit,
  type ConfiguredPlatformAdmin,
  type ConfiguredLlmTierMapping,
} from "./platformSetupStorageHelpers";

export function usePlatformSetupHydrationEffect(params: {
  readonly isAuthHydrating: boolean;
  readonly isAuthenticated: boolean;
  readonly currentUserEmail: string | null;
  readonly platformAdmin: ConfiguredPlatformAdmin | null;
  readonly hasMutatedSinceMountRef: React.MutableRefObject<boolean>;
  readonly applySnapshotToState: (next: CachedPlatformSetupState) => void;
  readonly resetAllSetupState: () => void;
  readonly setIsInitialLoading: (v: boolean) => void;
  readonly setPlatformAdmin: (v: ConfiguredPlatformAdmin | null) => void;
  readonly setAccostageCounts: (v: AccostagePg18CountsView | null) => void;
  readonly setLastSyncError: (v: string | null) => void;
}): void {
  const {
    isAuthHydrating,
    isAuthenticated,
    currentUserEmail,
    platformAdmin,
    hasMutatedSinceMountRef,
    applySnapshotToState,
    resetAllSetupState,
    setIsInitialLoading,
    setPlatformAdmin,
    setAccostageCounts,
    setLastSyncError,
  } = params;

  const prevIdentityRef = useRef<{ isAuthenticated: boolean; email: string | null }>({
    isAuthenticated,
    email: currentUserEmail,
  });

  useEffect(() => {
    const prev = prevIdentityRef.current;
    const normalizedPrev = prev.email?.trim().toLowerCase() ?? null;
    const normalizedNext = currentUserEmail?.trim().toLowerCase() ?? null;
    const loggedOut = prev.isAuthenticated && !isAuthenticated;
    const switchedUser =
      isAuthenticated &&
      normalizedPrev !== null &&
      normalizedNext !== null &&
      normalizedPrev !== normalizedNext;
    prevIdentityRef.current = { isAuthenticated, email: currentUserEmail };

    if (loggedOut || switchedUser) {
      hasMutatedSinceMountRef.current = false;
      writeStorageItem(PLATFORM_SETUP_STATE_STORAGE_KEY, null);
      applySnapshotToState(EMPTY_CACHED_PLATFORM_SETUP_STATE);
    }

    if (isAuthHydrating) {
      return;
    }
    let cancelled = false;
    let safetyTimer: ReturnType<typeof setTimeout> | undefined = setTimeout(() => {
      if (!cancelled) setIsInitialLoading(false);
    }, 5000);

    void fetchAndBuildHydrationOutcome({
      hasMutatedSinceMount: hasMutatedSinceMountRef.current,
      currentAdmin: platformAdmin,
      isAuthenticated,
      currentUserEmail,
    })
      .then((outcome) => {
        if (cancelled) return;
        if (outcome.kind === "BOOT_EPOCH_RESET") {
          hasMutatedSinceMountRef.current = false;
          useAuthSessionStore.getState().resetAuthSession();
          resetAllSetupState();
          return;
        }
        if (outcome.kind === "DAY0_CLEAN_RESET") {
          if (hasMutatedSinceMountRef.current) return;
          resetAllSetupState();
          return;
        }
        if (outcome.kind === "HYDRATED") {
          setAccostageCounts(outcome.accostageCounts);
          if (outcome.admin) setPlatformAdmin(outcome.admin);
          if (outcome.snapshot) applySnapshotToState(outcome.snapshot);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setLastSyncError(
            formatRfc9457ErrorToBanner(err, "fr", "Chargement initial plateforme").fullText,
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          if (safetyTimer) {
            clearTimeout(safetyTimer);
            safetyTimer = undefined;
          }
          setIsInitialLoading(false);
        }
      });

    return () => {
      cancelled = true;
      if (safetyTimer) clearTimeout(safetyTimer);
    };
  }, [isAuthHydrating, isAuthenticated, currentUserEmail]);
}

export async function executeRefreshAccostage(params: {
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly llmTiers: readonly ConfiguredLlmTierMapping[];
  readonly setAccostageCounts: (v: AccostagePg18CountsView) => void;
  readonly setLlmTiers: (v: readonly ConfiguredLlmTierMapping[]) => void;
  readonly buildSnapshot: (
    overrides: Partial<CachedPlatformSetupState>,
  ) => CachedPlatformSetupState;
}): Promise<void> {
  try {
    const client = createOrciaApiClient({ baseUrl: resolveWebApiBaseUrl() });
    const status = await client.getAccostageStatus();
    const nextCounts = buildAccostageCountsFromStatus(status, params.orgUnits);
    params.setAccostageCounts(nextCounts);
    if (nextCounts.modelsCount === 0 && params.llmTiers.length > 0) {
      params.setLlmTiers([]);
      writeCachedPlatformSetupState(params.buildSnapshot({ llmTiers: [] }));
    }
  } catch (err: unknown) {
    console.warn("[orcia:platformSetup.refreshAccostage]", err);
  }
}

export async function persistSetupSnapshotStrict(params: {
  readonly next: CachedPlatformSetupState;
  readonly hasMutatedSinceMountRef: React.MutableRefObject<boolean>;
  readonly setLastSyncError: (v: string | null) => void;
}): Promise<void> {
  params.hasMutatedSinceMountRef.current = true;
  writeCachedPlatformSetupState(params.next);
  try {
    await savePlatformSetupSnapshotToApi(params.next);
    params.setLastSyncError(null);
  } catch (err: unknown) {
    params.setLastSyncError(
      formatRfc9457ErrorToBanner(err, "fr", "Synchronisation plateforme").fullText,
    );
    throw err;
  }
}

export function mergeCachedPlatformSetupSnapshot(
  current: CachedPlatformSetupState,
  overrides: Partial<CachedPlatformSetupState>,
): CachedPlatformSetupState {
  return {
    orgUnits: overrides.orgUnits ?? current.orgUnits,
    rbacGrants: overrides.rbacGrants ?? current.rbacGrants,
    llmTiers: overrides.llmTiers ?? current.llmTiers,
    workspaces: overrides.workspaces ?? current.workspaces,
    datasources: overrides.datasources ?? current.datasources,
    packs: overrides.packs ?? current.packs,
    workflows: overrides.workflows ?? current.workflows,
    runs: overrides.runs ?? current.runs,
    catalogItems: overrides.catalogItems ?? current.catalogItems,
    ontologyConcepts: overrides.ontologyConcepts ?? current.ontologyConcepts,
    auditEvents: overrides.auditEvents ?? current.auditEvents,
  };
}
