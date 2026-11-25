import { createOrciaApiClient } from "@orcia/api-client";
import { useEffect, useRef } from "react";
import { DICTIONARIES, type SupportedWebLocale } from "../i18n";
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
  mergeCachedPlatformSetupSnapshot,
  mergeHydratedSnapshotWithLocalMutations,
  mergeWorkspacesPreferLocal,
  recordChangedSnapshotSlices,
  type PlatformSetupMutatedSlice,
} from "./platformSetupHydrationMappers";
import {
  PLATFORM_SETUP_STATE_STORAGE_KEY,
  writeCachedPlatformSetupState,
  writeStorageItem,
  type CachedPlatformSetupState,
  type ConfiguredOrgUnit,
  type ConfiguredPlatformAdmin,
  type ConfiguredLlmTierMapping,
} from "./platformSetupStorageHelpers";

export {
  mergeCachedPlatformSetupSnapshot,
  mergeHydratedSnapshotWithLocalMutations,
  mergeWorkspacesPreferLocal,
  recordChangedSnapshotSlices,
  type PlatformSetupMutatedSlice,
};

export function usePlatformSetupHydrationEffect(params: {
  readonly locale?: SupportedWebLocale;
  readonly isAuthHydrating: boolean;
  readonly isAuthenticated: boolean;
  readonly currentUserEmail: string | null;
  readonly platformAdmin: ConfiguredPlatformAdmin | null;
  readonly hasMutatedSinceMountRef: React.MutableRefObject<boolean>;
  readonly mutatedSlicesRef: React.MutableRefObject<Set<PlatformSetupMutatedSlice>>;
  readonly latestSnapshotRef: React.MutableRefObject<CachedPlatformSetupState>;
  readonly latestAdminRef: React.MutableRefObject<ConfiguredPlatformAdmin | null>;
  readonly applySnapshotToState: (next: CachedPlatformSetupState) => void;
  readonly resetAllSetupState: () => void;
  readonly setIsInitialLoading: (v: boolean) => void;
  readonly setPlatformAdmin: (v: ConfiguredPlatformAdmin | null) => void;
  readonly setAccostageCounts: (v: AccostagePg18CountsView | null) => void;
  readonly setLastSyncError: (v: string | null) => void;
}): void {
  const {
    locale = "fr",
    isAuthHydrating,
    isAuthenticated,
    currentUserEmail,
    platformAdmin,
    hasMutatedSinceMountRef,
    mutatedSlicesRef,
    latestSnapshotRef,
    latestAdminRef,
    applySnapshotToState,
    resetAllSetupState,
    setIsInitialLoading,
    setPlatformAdmin,
    setAccostageCounts,
    setLastSyncError,
  } = params;

  const localeRef = useRef<SupportedWebLocale>(locale);
  localeRef.current = locale;

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
      mutatedSlicesRef.current.clear();
      latestAdminRef.current = null;
      writeStorageItem(PLATFORM_SETUP_STATE_STORAGE_KEY, null);
      applySnapshotToState(EMPTY_CACHED_PLATFORM_SETUP_STATE);
    }

    if (isAuthHydrating) {
      return;
    }
    let cancelled = false;
    const wasMutatedBeforeFetch = hasMutatedSinceMountRef.current;
    let safetyTimer: ReturnType<typeof setTimeout> | undefined = setTimeout(() => {
      if (!cancelled) setIsInitialLoading(false);
    }, 5000);

    void fetchAndBuildHydrationOutcome({
      hasMutatedSinceMount: wasMutatedBeforeFetch,
      currentAdmin: platformAdmin,
      isAuthenticated,
      currentUserEmail,
      locale: localeRef.current,
    })
      .then((outcome) => {
        if (cancelled) return;
        if (outcome.kind === "BOOT_EPOCH_RESET") {
          hasMutatedSinceMountRef.current = false;
          mutatedSlicesRef.current.clear();
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
          // Always apply server-derived accostage counts even if a local mutation ran mid-flight.
          setAccostageCounts(outcome.accostageCounts);
          if (
            outcome.admin &&
            (!mutatedSlicesRef.current.has("admin") || latestAdminRef.current === null)
          ) {
            setPlatformAdmin(outcome.admin);
          }
          if (outcome.snapshot) {
            const hasLocalSliceMutations = mutatedSlicesRef.current.size > 0;
            const nextSnapshot = hasLocalSliceMutations
              ? mergeHydratedSnapshotWithLocalMutations({
                  hydrated: outcome.snapshot,
                  local: latestSnapshotRef.current,
                  mutatedSlices: mutatedSlicesRef.current,
                })
              : outcome.snapshot;
            applySnapshotToState(nextSnapshot);
            if (hasLocalSliceMutations) {
              writeCachedPlatformSetupState(nextSnapshot);
            }
          }
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const activeLocale = localeRef.current;
          const copy = DICTIONARIES[activeLocale].shellChrome.platformSetupGovernance;
          setLastSyncError(
            formatRfc9457ErrorToBanner(err, activeLocale, copy.platformInitialLoadErrorContext)
              .fullText,
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
  readonly locale?: SupportedWebLocale;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly llmTiers: readonly ConfiguredLlmTierMapping[];
  readonly setAccostageCounts: (v: AccostagePg18CountsView) => void;
  readonly setLlmTiers: (v: readonly ConfiguredLlmTierMapping[]) => void;
  readonly buildSnapshot: (
    overrides: Partial<CachedPlatformSetupState>,
  ) => CachedPlatformSetupState;
  readonly persistLocalSnapshot?: (next: CachedPlatformSetupState) => void;
}): Promise<void> {
  try {
    const client = createOrciaApiClient({
      baseUrl: resolveWebApiBaseUrl(),
      locale: params.locale ?? "fr",
    });
    const status = await client.getAccostageStatus();
    const nextCounts = buildAccostageCountsFromStatus(status, params.orgUnits);
    params.setAccostageCounts(nextCounts);
    if (nextCounts.modelsCount === 0 && params.llmTiers.length > 0) {
      params.setLlmTiers([]);
      const nextSnapshot = params.buildSnapshot({ llmTiers: [] });
      (params.persistLocalSnapshot ?? writeCachedPlatformSetupState)(nextSnapshot);
    }
  } catch (err: unknown) {
    console.warn("[orcia:platformSetup.refreshAccostage]", err);
  }
}

export async function persistSetupSnapshotStrict(params: {
  readonly locale?: SupportedWebLocale;
  readonly next: CachedPlatformSetupState;
  readonly hasMutatedSinceMountRef: React.MutableRefObject<boolean>;
  readonly mutatedSlicesRef: React.MutableRefObject<Set<PlatformSetupMutatedSlice>>;
  readonly latestSnapshotRef: React.MutableRefObject<CachedPlatformSetupState>;
  readonly setLastSyncError: (v: string | null) => void;
}): Promise<void> {
  const resolvedLocale = params.locale ?? "fr";
  params.hasMutatedSinceMountRef.current = true;
  recordChangedSnapshotSlices(
    params.latestSnapshotRef.current,
    params.next,
    params.mutatedSlicesRef.current,
  );
  params.latestSnapshotRef.current = params.next;
  try {
    await savePlatformSetupSnapshotToApi(params.next, resolvedLocale);
    writeCachedPlatformSetupState(params.next);
    params.setLastSyncError(null);
  } catch (err: unknown) {
    const copy = DICTIONARIES[resolvedLocale].shellChrome.platformSetupGovernance;
    params.setLastSyncError(
      formatRfc9457ErrorToBanner(err, resolvedLocale, copy.platformSyncErrorContext).fullText,
    );
    throw err;
  }
}
