import {
  ActivityLogExplorerView,
  ActivityProvenanceModal,
  OrciaAlertBanner,
  type UiActivityLogEventItem,
  type UiActivityScopeFilterOption,
} from "@orcia/ui";
import { createRoute } from "@tanstack/react-router";
import React, { useEffect, useState } from "react";
import {
  cleanAuditSummaryJargon,
  formatHumanReadableScopePath,
  usePlatformSetup,
} from "../components/platformSetupStore";
import { useShellNavigation } from "../components/ShellContainer";
import { useI18n } from "../i18n";
import { canObserveGlobalAuditScope, useAuthSessionStore } from "../stores/authSessionStore";
import {
  exportRunProvenanceFromApi,
  fetchAuditLedgerFromApi,
  fetchRunProvenanceFromApi,
  type AuditProvenanceSummaryResponse,
} from "./activityApiBridge";
import {
  buildActivityScopeOptions,
  formatActivityTimestamp,
} from "./activityFormatters";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";

export function ActivityLogRouteView(): React.ReactElement {
  const { locale, isFr, dictionary } = useI18n();
  const activityDict = dictionary.activity;
  const eventLabels = dictionary.routesAndWizards.activityEvents;
  const { activeScopeId, openHelpSection } = useShellNavigation();
  const { platformAdmin, orgUnits, workspaces, scopes } = usePlatformSetup();
  const roles = useAuthSessionStore((s) => s.roles);
  const activeHat = useAuthSessionStore((s) => s.activeHat);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const allowGlobalScope = canObserveGlobalAuditScope({ roles, activeHat, readOnlyObserver });

  const [apiEvents, setApiEvents] = useState<readonly UiActivityLogEventItem[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | undefined>(undefined);
  const [provenanceSummary, setProvenanceSummary] = useState<AuditProvenanceSummaryResponse | null>(null);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [apiErrorMessage, setApiErrorMessage] = useState<string | null>(null);

  // Fetch immutable events from PostgreSQL 18 audit_ledger via @orcia/api-client
  useEffect(() => {
    let isCancelled = false;
    void (async () => {
      const res = await fetchAuditLedgerFromApi(locale, { limit: 500 });
      if (isCancelled) return;
      if (res.ok && Array.isArray(res.entries)) {
        const mapped = res.entries.map((e) => {
          const resolvedType = eventLabels[e.event_type] ?? {
            label: activityDict.recordedAction,
            tone: "cobalt" as const,
          };
          const rawScope = e.scope_path || "GLOBAL";
          const resolvedScopeLabel = formatHumanReadableScopePath(rawScope, locale);
          const createdAtIso = e.created_at || new Date().toISOString();
          return {
            id: e.id,
            timestampIso: createdAtIso,
            formattedTimestamp: formatActivityTimestamp(createdAtIso, isFr, locale),
            eventType: e.event_type,
            eventTypeLabel: resolvedType.label,
            badgeTone: resolvedType.tone,
            summary: cleanAuditSummaryJargon(e.summary, locale),
            actorName: e.actor_display_name || e.actor_id,
            actorEmail: e.actor_email || undefined,
            scopeId: e.workspace_id || e.org_unit_id || undefined,
            scopePath: rawScope,
            scopeLabel: resolvedScopeLabel,
            runId: e.run_id || undefined,
          };
        });
        setApiEvents(mapped);
        setApiErrorMessage(null);
      } else if (!res.ok) {
        setApiErrorMessage(res.errorMessage);
      }
    })();
    return () => {
      isCancelled = true;
    };
  }, [locale, isFr, eventLabels, activityDict.recordedAction]);

  const connectedUserName = platformAdmin?.displayName ?? activityDict.connectedAdminFallback;

  const scopeOptions: UiActivityScopeFilterOption[] = buildActivityScopeOptions(
    orgUnits,
    workspaces,
    {
      entirePlatform: activityDict.entirePlatform,
      divisionPrefix: activityDict.divisionPrefix,
      teamPrefix: activityDict.teamPrefix,
      privateSpacePrefix: activityDict.privateSpacePrefix,
      spacePrefix: activityDict.spacePrefix,
    },
    { includeGlobal: allowGlobalScope },
  );

  const effectiveActiveScopeId =
    !allowGlobalScope && (activeScopeId === "scope-global" || activeScopeId === "ALL")
      ? (scopeOptions[0]?.id ?? activeScopeId)
      : activeScopeId;

  const activeScopeNode = scopes.find((s) => s.id === effectiveActiveScopeId);
  const activeObservationOption = scopeOptions.find((o) => o.id === effectiveActiveScopeId);
  const activeObservationScopeLabel =
    activeObservationOption?.label ??
    (allowGlobalScope && activeScopeNode?.level === "GLOBAL"
      ? activityDict.entirePlatform
      : (activeScopeNode?.name ?? scopeOptions[0]?.label ?? ""));

  // Pure source of truth: PostgreSQL 18 audit_ledger via apiEvents (zero local store fallback)
  const effectiveEvents: readonly UiActivityLogEventItem[] = apiEvents;

  const handleInspectProvenance = async (runId: string) => {
    const res = await fetchRunProvenanceFromApi(runId, locale);
    if (res.ok) {
      setProvenanceSummary(res.summary);
      setApiErrorMessage(null);
    } else {
      setApiErrorMessage(res.errorMessage);
    }
  };

  const handleExportProvenance = async (runId: string, format: "json" | "md") => {
    setIsExporting(true);
    const res = await exportRunProvenanceFromApi(runId, format, locale);
    setIsExporting(false);
    if (!res.ok) {
      setApiErrorMessage(res.errorMessage);
    }
  };

  return (
    <>
      {apiErrorMessage && (
        <div style={{ marginBottom: "12px" }}>
          <OrciaAlertBanner tone="amber" title={activityDict.ledgerNoticeTitle}>
            {apiErrorMessage}
          </OrciaAlertBanner>
        </div>
      )}

      {provenanceSummary && (
        <ActivityProvenanceModal
          summary={provenanceSummary}
          labels={activityDict.provenanceModal}
          onClose={() => setProvenanceSummary(null)}
        />
      )}

      <ActivityLogExplorerView
        events={effectiveEvents}
        scopeOptions={scopeOptions}
        activeObservationScopeId={effectiveActiveScopeId}
        activeObservationScopeLabel={activeObservationScopeLabel}
        allowAllScopesOption={allowGlobalScope}
        connectedUserName={connectedUserName}
        labels={activityDict.explorer}
        provenanceLabels={activityDict.provenanceExport}
        onOpenHelpSection={openHelpSection}
        selectedRunId={selectedRunId}
        onSelectRunId={setSelectedRunId}
        onInspectProvenance={handleInspectProvenance}
        onExportProvenance={handleExportProvenance}
        isExporting={isExporting}
      />
    </>
  );
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/activity",
  validateSearch: validateOrciaRouteSearch,
  component: ActivityLogRouteView,
});
