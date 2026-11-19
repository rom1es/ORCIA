import {
  StatusBadge,
  type ControlCenterRunItem,
  type ControlCenterWorkspaceGovItem,
} from "@orcia/ui";
import React from "react";
import type { ConfiguredWorkflowItem } from "../../components/platformSetupStore";

export interface CockpitRunsSectionProps {
  readonly isFr: boolean;
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly availableWorkspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly workflows: readonly ConfiguredWorkflowItem[];
  readonly scopedRuns: readonly ControlCenterRunItem[];
  readonly selectedWsId: string;
  readonly selectedWfKey: string;
  readonly runTitle: string;
  readonly onSelectWsId: (id: string) => void;
  readonly onSelectWfKey: (key: string) => void;
  readonly onChangeRunTitle: (title: string) => void;
  readonly onLaunchRun: (event: React.FormEvent) => void;
  readonly onNavigateToWorkspaces: () => void;
}

export function CockpitRunsSection({
  isFr,
  workspaces,
  availableWorkspaces,
  workflows,
  scopedRuns,
  selectedWsId,
  selectedWfKey,
  runTitle,
  onSelectWsId,
  onSelectWfKey,
  onChangeRunTitle,
  onLaunchRun,
  onNavigateToWorkspaces,
}: CockpitRunsSectionProps): React.ReactElement {
  return (
    <section
      data-testid="cockpit-prompt-and-runs-section"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "14px" }}
    >
      {workspaces.length === 0 ? (
        <div
          data-testid="cockpit-no-workspace-empty-state"
          style={{
            padding: "16px",
            borderRadius: "var(--radius-md)",
            border: "1px dashed var(--color-border)",
            backgroundColor: "var(--color-surface-bg)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div>
            <strong>
              {isFr
                ? "Aucun Espace de Travail ni processus en cours"
                : "No Workspace or active process yet"}
            </strong>
            <p
              style={{
                margin: "4px 0 0 0",
                fontSize: "13px",
                color: "var(--color-muted-foreground)",
              }}
            >
              {isFr
                ? "Créez votre premier Espace de Travail pour lancer vos processus, utiliser Mon Assistant et suivre vos validations."
                : "Create your first Workspace to run processes, use My Assistant, and track your reviews."}
            </p>
          </div>
          <button
            type="button"
            data-testid="cockpit-go-create-workspace-btn"
            onClick={onNavigateToWorkspaces}
            style={{
              padding: "7px 14px",
              borderRadius: "var(--radius-sm)",
              border: "none",
              backgroundColor: "var(--color-primary-cobalt)",
              color: "var(--color-primary-foreground)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {isFr ? "+ Créer un Espace de Travail" : "+ Create a Workspace"}
          </button>
        </div>
      ) : (
        <form
          data-testid="cockpit-launch-run-form"
          autoComplete="off"
          data-lpignore="true"
          data-form-type="other"
          onSubmit={onLaunchRun}
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "10px",
            alignItems: "center",
            padding: "12px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-bg)",
          }}
        >
          <select
            data-testid="cockpit-select-workspace"
            value={selectedWsId || availableWorkspaces[0]?.workspaceId || ""}
            onChange={(e) => onSelectWsId(e.target.value)}
            style={{
              padding: "7px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              maxWidth: "100%",
              minWidth: 0,
              boxSizing: "border-box",
            }}
          >
            {availableWorkspaces.map((ws) => (
              <option key={ws.workspaceId} value={ws.workspaceId}>
                {ws.name}
              </option>
            ))}
          </select>

          <select
            data-testid="cockpit-select-workflow"
            value={selectedWfKey || workflows[0]?.workflowKey || "assistant-agent"}
            onChange={(e) => onSelectWfKey(e.target.value)}
            style={{
              padding: "7px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              maxWidth: "100%",
              minWidth: 0,
              boxSizing: "border-box",
            }}
          >
            <option value="assistant-agent">
              {isFr ? "Assistant ORCIA (Processus standard)" : "ORCIA Assistant (Standard process)"}
            </option>
            {workflows.map((wf) => (
              <option key={wf.workflowKey} value={wf.workflowKey}>
                {wf.title} (v{wf.version})
              </option>
            ))}
          </select>

          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="cockpit-run-title-input"
            value={runTitle}
            onChange={(e) => onChangeRunTitle(e.target.value)}
            placeholder={isFr ? "Intitulé de l'exécution..." : "Execution title..."}
            style={{
              flex: "1 1 200px",
              minWidth: 0,
              maxWidth: "100%",
              boxSizing: "border-box",
              padding: "7px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
            }}
          />

          <button
            type="submit"
            data-testid="cockpit-launch-run-submit-btn"
            style={{
              padding: "7px 14px",
              borderRadius: "var(--radius-sm)",
              border: "none",
              backgroundColor: "var(--color-primary-cobalt)",
              color: "var(--color-primary-foreground)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {isFr ? "Démarrer le processus" : "Start process"}
          </button>
        </form>
      )}

      {scopedRuns.length > 0 && (
        <div
          data-testid="cockpit-active-runs-list"
          style={{ display: "grid", gap: "8px" }}
        >
          {scopedRuns.map((run) => (
            <div
              key={run.runId}
              data-testid={`cockpit-run-card-${run.runId}`}
              style={{
                padding: "10px 12px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                backgroundColor: "var(--color-surface-bg)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <strong>{run.title}</strong>
                <span
                  style={{
                    marginLeft: "8px",
                    fontSize: "12px",
                    color: "var(--color-muted-foreground)",
                  }}
                >
                  ({run.workspaceName} · {run.currentStepKey})
                </span>
              </div>
              <StatusBadge label={run.status} tone="emerald" monospace />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
