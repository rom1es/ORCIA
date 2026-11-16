import {
  ActivityLogExplorerView,
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
import {
  exportRunProvenanceFromApi,
  fetchAuditLedgerFromApi,
  fetchRunProvenanceFromApi,
  type AuditProvenanceSummaryResponse,
} from "./activityApiBridge";
import {
  buildActivityScopeOptions,
  EVENT_TYPE_EN_LABELS,
  EVENT_TYPE_FR_LABELS,
  formatActivityTimestamp,
} from "./activityFormatters";
import { ActivityProvenanceModal } from "./ActivityProvenanceModal";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";

export function ActivityLogRouteView(): React.ReactElement {
  const { locale, dictionary } = useI18n();
  const activityDict = dictionary.activity;
  const isFr = locale === "fr";
  const { activeScopeId, openHelpSection } = useShellNavigation();
  const { platformAdmin, orgUnits, workspaces, scopes } = usePlatformSetup();

  const [apiEvents, setApiEvents] = useState<readonly UiActivityLogEventItem[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | undefined>(undefined);
  const [provenanceSummary, setProvenanceSummary] = useState<AuditProvenanceSummaryResponse | null>(null);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [apiErrorMessage, setApiErrorMessage] = useState<string | null>(null);

  // Fetch immutable events from PostgreSQL 18 audit_ledger via @orcia/api-client
  useEffect(() => {
    let isCancelled = false;
    void (async () => {
      const res = await fetchAuditLedgerFromApi(isFr ? "fr" : "en", { limit: 500 });
      if (isCancelled) return;
      if (res.ok && Array.isArray(res.entries)) {
        const typeMap = isFr ? EVENT_TYPE_FR_LABELS : EVENT_TYPE_EN_LABELS;
        const mapped = res.entries.map((e) => {
          const resolvedType = typeMap[e.event_type] ?? {
            label: activityDict.recordedAction,
            tone: "cobalt" as const,
          };
          const rawScope = e.scope_path || "GLOBAL";
          const resolvedScopeLabel = formatHumanReadableScopePath(rawScope);
          const createdAtIso = e.created_at || new Date().toISOString();
          return {
            id: e.id,
            timestampIso: createdAtIso,
            formattedTimestamp: formatActivityTimestamp(createdAtIso, isFr),
            eventType: e.event_type,
            eventTypeLabel: resolvedType.label,
            badgeTone: resolvedType.tone,
            summary: cleanAuditSummaryJargon(e.summary),
            actorName: e.actor_display_name || e.actor_id,
            actorEmail: e.actor_email || undefined,
            scopeId: e.workspace_id || undefined,
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
  }, [isFr, activityDict.recordedAction]);

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
  );

  const activeScopeNode = scopes.find((s) => s.id === activeScopeId);
  const activeObservationOption = scopeOptions.find((o) => o.id === activeScopeId);
  const activeObservationScopeLabel =
    activeObservationOption?.label ??
    (activeScopeNode?.level === "GLOBAL"
      ? activityDict.entirePlatform
      : (activeScopeNode?.name ?? activityDict.entirePlatform));

  // Pure source of truth: PostgreSQL 18 audit_ledger via apiEvents (zero local store fallback)
  const effectiveEvents: readonly UiActivityLogEventItem[] = apiEvents;

  const handleInspectProvenance = async (runId: string) => {
    const res = await fetchRunProvenanceFromApi(runId, isFr ? "fr" : "en");
    if (res.ok) {
      setProvenanceSummary(res.summary);
      setApiErrorMessage(null);
    } else {
      setApiErrorMessage(res.errorMessage);
    }
  };

  const handleExportProvenance = async (runId: string, format: "json" | "md") => {
    setIsExporting(true);
    const res = await exportRunProvenanceFromApi(runId, format, isFr ? "fr" : "en");
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
        activeObservationScopeId={activeScopeId}
        activeObservationScopeLabel={activeObservationScopeLabel}
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
