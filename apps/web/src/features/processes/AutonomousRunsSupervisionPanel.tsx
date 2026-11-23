import {
  createOrciaApiClient,
  type AutonomousRunSupervisionItemSchema,
} from "@orcia/api-client";
import { AutonomousExecutionBadge, OrciaAlertBanner } from "@orcia/ui";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
import { formatCurrency } from "../../lib/formatters";

const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const SETUP_WS_REGEX = /^ws-\d+$/;

function isWorkspaceKey(id: string): boolean {
  return UUID_REGEX.test(id) || SETUP_WS_REGEX.test(id);
}

export function AutonomousRunsSupervisionPanel(): React.ReactElement | null {
  const { dictionary, locale } = useI18n();
  const { activeScopeId, openHelpSection } = useShellNavigation();
  const { scopes, workspaces } = usePlatformSetup();
  const labels = dictionary.autonomousSupervision;

  const [runs, setRuns] = useState<AutonomousRunSupervisionItemSchema[]>([]);
  const [busyRunId, setBusyRunId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const activeWorkspaceId = useMemo(() => {
    const scopeRaw = activeScopeId.startsWith("scope-ws-")
      ? activeScopeId.slice("scope-ws-".length)
      : activeScopeId;
    if (isWorkspaceKey(scopeRaw)) {
      return scopeRaw;
    }
    const activeScope = scopes.find((s) => s.id === activeScopeId);
    if (activeScope?.level === "WORKSPACE" && isWorkspaceKey(activeScope.id)) {
      return activeScope.id;
    }
    const wsFromScopes = scopes.find(
      (s) => s.level === "WORKSPACE" && isWorkspaceKey(s.id),
    )?.id;
    if (wsFromScopes) {
      return wsFromScopes;
    }
    const wsFromList = workspaces.find((w) => isWorkspaceKey(w.workspaceId))?.workspaceId;
    return wsFromList ?? null;
  }, [activeScopeId, scopes, workspaces]);

  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "" }), []);

  const loadAutonomousRuns = useCallback(async () => {
    if (!activeWorkspaceId) {
      setRuns([]);
      return;
    }
    try {
      setErrorMessage(null);
      const res = await apiClient.listWorkspaceAutonomousRuns(activeWorkspaceId);
      setRuns(res.runs ?? []);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : labels.loadErrorBanner);
    }
  }, [activeWorkspaceId, apiClient, labels.loadErrorBanner]);

  useEffect(() => {
    void loadAutonomousRuns();
  }, [loadAutonomousRuns]);

  const handleEmergencyStop = useCallback(
    async (runId: string) => {
      try {
        setBusyRunId(runId);
        setErrorMessage(null);
        setSuccessMessage(null);
        await apiClient.emergencyStopAutonomousRun(runId, {
          reason: "",
          suspend_trigger: true,
          workspace_id: activeWorkspaceId ?? undefined,
        });
        setSuccessMessage(labels.emergencyStopSuccessBanner);
        await loadAutonomousRuns();
      } catch (err: unknown) {
        setErrorMessage(err instanceof Error ? err.message : labels.loadErrorBanner);
      } finally {
        setBusyRunId(null);
      }
    },
    [
      activeWorkspaceId,
      apiClient,
      labels.emergencyStopSuccessBanner,
      labels.loadErrorBanner,
      loadAutonomousRuns,
    ],
  );

  const handleInvalidateAndRestore = useCallback(
    async (runId: string) => {
      try {
        setBusyRunId(runId);
        setErrorMessage(null);
        setSuccessMessage(null);
        await apiClient.invalidateAndRestoreAutonomousRun(runId, {
          comment: "",
          workspace_id: activeWorkspaceId ?? undefined,
        });
        setSuccessMessage(labels.restoreSuccessBanner);
        await loadAutonomousRuns();
      } catch (err: unknown) {
        setErrorMessage(err instanceof Error ? err.message : labels.loadErrorBanner);
      } finally {
        setBusyRunId(null);
      }
    },
    [
      activeWorkspaceId,
      apiClient,
      labels.loadErrorBanner,
      labels.restoreSuccessBanner,
      loadAutonomousRuns,
    ],
  );

  if (!activeWorkspaceId && runs.length === 0 && !errorMessage) {
    return null;
  }

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

      {runs.length === 0 ? (
        <p
          data-testid="processes-autonomous-supervision-empty"
          style={{ margin: 0, fontSize: "12.5px", color: "var(--color-text-muted)" }}
        >
          {labels.emptyStateText}
        </p>
      ) : (
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
      )}
    </div>
  );
}
