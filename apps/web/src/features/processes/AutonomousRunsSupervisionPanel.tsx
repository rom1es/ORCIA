import {
  createOrciaApiClient,
  type AutonomousRunSupervisionItemSchema,
} from "@orcia/api-client";
import { AutonomousExecutionBadge, OrciaAlertBanner } from "@orcia/ui";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import { formatCurrency } from "../../lib/formatters";

const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function AutonomousRunsSupervisionPanel(): React.ReactElement | null {
  const { dictionary, locale } = useI18n();
  const { activeScopeId, openHelpSection } = useShellNavigation();
  const { scopes, workspaces } = usePlatformSetup();
  const labels = dictionary.autonomousSupervision;

  const [runs, setRuns] = useState<AutonomousRunSupervisionItemSchema[]>([]);
  const [busyRunId, setBusyRunId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const scopeTarget = useMemo(() => {
    const scopeRaw = activeScopeId.startsWith("scope-ws-")
      ? activeScopeId.slice("scope-ws-".length)
      : activeScopeId;
    if (!UUID_REGEX.test(scopeRaw)) {
      return { exactWorkspaceId: null, orgScopeId: null };
    }
    const matchingScope = scopes.find((s) => s.id === activeScopeId || s.id === scopeRaw);
    if (
      matchingScope?.level === "WORKSPACE" ||
      workspaces.some((w) => w.workspaceId === scopeRaw)
    ) {
      return { exactWorkspaceId: scopeRaw, orgScopeId: null };
    }
    if (matchingScope?.level === "BU" || matchingScope?.level === "TEAM") {
      return { exactWorkspaceId: null, orgScopeId: scopeRaw };
    }
    return { exactWorkspaceId: null, orgScopeId: null };
  }, [activeScopeId, scopes, workspaces]);

  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "" }), []);

  const loadAutonomousRuns = useCallback(async () => {
    try {
      setErrorMessage(null);
      const res = scopeTarget.exactWorkspaceId
        ? await apiClient.listWorkspaceAutonomousRuns(scopeTarget.exactWorkspaceId)
        : await apiClient.listAutonomousRuns(
            scopeTarget.orgScopeId ? { scopeId: scopeTarget.orgScopeId } : undefined,
          );
      setRuns(res.runs ?? []);
    } catch (err: unknown) {
      setRuns([]);
      const formatted = formatRfc9457ErrorToBanner(err, locale, labels.panelTitle).fullText;
      setErrorMessage(formatted || (err instanceof Error ? err.message : labels.loadErrorBanner));
    }
  }, [
    apiClient,
    labels.loadErrorBanner,
    labels.panelTitle,
    locale,
    scopeTarget.exactWorkspaceId,
    scopeTarget.orgScopeId,
  ]);

  useEffect(() => {
    void loadAutonomousRuns();
  }, [loadAutonomousRuns]);

  const handleEmergencyStop = useCallback(
    async (runId: string) => {
      try {
        setBusyRunId(runId);
        setErrorMessage(null);
        setSuccessMessage(null);
        const targetRun = runs.find((r) => r.run_id === runId);
        await apiClient.emergencyStopAutonomousRun(runId, {
          reason: "",
          suspend_trigger: true,
          workspace_id: scopeTarget.exactWorkspaceId ?? targetRun?.workspace_id ?? undefined,
        });
        setSuccessMessage(labels.emergencyStopSuccessBanner);
        await loadAutonomousRuns();
      } catch (err: unknown) {
        const formatted = formatRfc9457ErrorToBanner(err, locale, labels.panelTitle).fullText;
        setErrorMessage(formatted || (err instanceof Error ? err.message : labels.loadErrorBanner));
      } finally {
        setBusyRunId(null);
      }
    },
    [
      apiClient,
      labels.emergencyStopSuccessBanner,
      labels.loadErrorBanner,
      labels.panelTitle,
      loadAutonomousRuns,
      locale,
      runs,
      scopeTarget.exactWorkspaceId,
    ],
  );

  const handleInvalidateAndRestore = useCallback(
    async (runId: string) => {
      try {
        setBusyRunId(runId);
        setErrorMessage(null);
        setSuccessMessage(null);
        const targetRun = runs.find((r) => r.run_id === runId);
        await apiClient.invalidateAndRestoreAutonomousRun(runId, {
          comment: "",
          workspace_id: scopeTarget.exactWorkspaceId ?? targetRun?.workspace_id ?? undefined,
        });
        setSuccessMessage(labels.restoreSuccessBanner);
        await loadAutonomousRuns();
      } catch (err: unknown) {
        const formatted = formatRfc9457ErrorToBanner(err, locale, labels.panelTitle).fullText;
        setErrorMessage(formatted || (err instanceof Error ? err.message : labels.loadErrorBanner));
      } finally {
        setBusyRunId(null);
      }
    },
    [
      apiClient,
      labels.loadErrorBanner,
      labels.panelTitle,
      labels.restoreSuccessBanner,
      loadAutonomousRuns,
      locale,
      runs,
      scopeTarget.exactWorkspaceId,
    ],
  );

  return (
    <div
      data-testid="processes-autonomous-supervision-panel"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "12px" }}
    >
      <div>
        <h3 style={{ margin: 0, fontSize: "var(--font-size-h3)" }}>{labels.panelTitle}</h3>
        <p style={{ margin: "2px 0 0 0", fontSize: "12.5px", color: "var(--color-text-secondary)" }}>
          {labels.panelSubtitle}
        </p>
      </div>

      {errorMessage && (
        <OrciaAlertBanner tone="crimson" role="alert" testId="autonomous-supervision-error-banner">
          {errorMessage}
        </OrciaAlertBanner>
      )}
      {successMessage && (
        <OrciaAlertBanner tone="emerald" role="status" testId="autonomous-supervision-success-banner">
          {successMessage}
        </OrciaAlertBanner>
      )}

      {!errorMessage && runs.length === 0 ? (
        <p
          data-testid="processes-autonomous-supervision-empty"
          style={{ margin: 0, fontSize: "12.5px", color: "var(--color-text-muted)" }}
        >
          {labels.emptyStateText}
        </p>
      ) : runs.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {runs.map((run) => (
            <div
              key={run.run_id}
              data-testid={`autonomous-supervised-run-${run.run_id}`}
              className="rounded-lg border p-3"
              style={{
                backgroundColor: "var(--color-bg-elevated)",
                borderColor: "var(--color-border-subtle)",
                display: "flex",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "8px",
                }}
              >
                <strong style={{ fontSize: "13.5px", color: "var(--color-text-primary)" }}>
                  {run.workflow_title}
                </strong>
                <span style={{ fontSize: "11.5px", color: "var(--color-text-muted)" }}>
                  {formatCurrency(run.cost_usd, locale)}
                </span>
              </div>

              <AutonomousExecutionBadge
                testId={`autonomous-run-badge-${run.run_id}`}
                runId={run.run_id}
                triggerLabel={run.trigger_label}
                runStatus={run.run_status}
                busy={busyRunId === run.run_id}
                labels={labels.badge}
                onEmergencyStop={(rid) => void handleEmergencyStop(rid)}
                onInvalidateAndRestore={(rid) => void handleInvalidateAndRestore(rid)}
                onOpenHelpSection={openHelpSection}
              />
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
