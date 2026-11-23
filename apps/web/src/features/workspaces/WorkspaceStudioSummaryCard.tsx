import {
  getOrciaIconGlyph,
  OrciaIcon,
  type ControlCenterWorkspaceGovItem,
  type ProductLifecyclePhaseType,
  type WorkspaceVisibilityMode,
} from "@orcia/ui";
import React from "react";
import { resolveGlobalScopeLabel } from "../../components/platformSetupWorkspaces";
import {
  formatI18nTemplate,
  resolveDictionaryForFlag,
  resolveLocaleForFlag,
} from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import { formatCurrency } from "../../lib/formatters";
import { formatPackCountNoun } from "../settings/packs/packDisplayFormatters";

export interface WorkspaceStudioSummaryCardProps {
  readonly ws: ControlCenterWorkspaceGovItem;
  readonly isFr: boolean;
  readonly isSelected: boolean;
  readonly isAutosaved: boolean;
  readonly wsSourcesCount: number;
  readonly ontologyConceptsCount: number;
  readonly workflowsCount: number;
  readonly inputStyle: React.CSSProperties;
  readonly onSelectWorkspace: (workspaceId: string) => void;
  readonly onUpdateWorkspacePhase: (
    workspaceId: string,
    phase: ProductLifecyclePhaseType,
  ) => void | Promise<void>;
  readonly onUpdateWorkspaceVisibility: (
    workspaceId: string,
    visibilityMode: WorkspaceVisibilityMode,
  ) => void | Promise<void>;
  readonly onMarkAutosaved: (workspaceId: string) => void;
  readonly onFeedback: (message: string) => void;
  readonly onNavigateToRoute: (route: string) => void;
}

export function WorkspaceStudioSummaryCard({
  ws,
  isFr,
  isSelected,
  isAutosaved,
  wsSourcesCount,
  ontologyConceptsCount,
  workflowsCount,
  inputStyle,
  onSelectWorkspace,
  onUpdateWorkspacePhase,
  onUpdateWorkspaceVisibility,
  onMarkAutosaved,
  onFeedback,
  onNavigateToRoute,
}: WorkspaceStudioSummaryCardProps): React.ReactElement {
  const resolvedLocale = resolveLocaleForFlag(isFr);
  const cardCopy = resolveDictionaryForFlag(isFr, resolvedLocale).featureWorkspaces.summaryCard;
  const visibilityIconName =
    ws.visibilityMode === "PRIVATE_USER"
      ? "lock"
      : ws.visibilityMode === "CONFIDENTIAL_RESTRICTED"
        ? "shield"
        : "team";
  const visibilityLabelText =
    ws.visibilityMode === "PRIVATE_USER"
      ? cardCopy.visibilityPrivate
      : ws.visibilityMode === "CONFIDENTIAL_RESTRICTED"
        ? cardCopy.visibilityConfidential
        : cardCopy.visibilityStandard;

  return (
    <div
      data-testid={`workspace-studio-card-${ws.workspaceId}`}
      className="orcia-bento-card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        border: isSelected ? "2px solid var(--color-action-primary)" : "1px solid var(--color-border)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
        <div>
          <strong style={{ fontSize: "15px" }}>{ws.name}</strong>
          <div style={{ fontSize: "11px", color: "var(--color-muted-foreground)", marginTop: "2px" }}>
            {cardCopy.billingTeamLabel}{" "}
            <strong>{ws.ownerOrgUnitName ?? resolveGlobalScopeLabel(isFr)}</strong>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          {isAutosaved && (
            <span
              data-testid={`workspace-autosaved-badge-${ws.workspaceId}`}
              style={{
                fontSize: "11px",
                fontWeight: 700,
                padding: "2px 8px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--color-action-primary-subtle)",
                color: "var(--color-status-success)",
              }}
            >
              <OrciaIcon name="check" /> {cardCopy.savedBadge}
            </span>
          )}
          <span
            data-testid={`workspace-visibility-badge-${ws.workspaceId}`}
            style={{
              fontSize: "11px",
              fontWeight: 600,
              padding: "3px 8px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--color-bg-elevated)",
              border: "1px solid var(--color-border-subtle)",
            }}
          >
            <OrciaIcon name={visibilityIconName} /> {visibilityLabelText}
          </span>
        </div>
      </div>

      {wsSourcesCount > 0 || ontologyConceptsCount > 0 || workflowsCount > 0 || (ws.finopsCostUsd ?? 0) > 0 ? (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", fontSize: "11px", color: "var(--color-text-secondary)" }}>
          {wsSourcesCount > 0 && (
            <span>
              <OrciaIcon name="books" /> <strong>{wsSourcesCount}</strong>{" "}
              {formatPackCountNoun(wsSourcesCount, cardCopy.attachedSourceSingular, cardCopy.attachedSourcePlural, isFr)}
            </span>
          )}
          {ontologyConceptsCount > 0 && (
            <span>
              <OrciaIcon name="bookOpen" /> <strong>{ontologyConceptsCount}</strong>{" "}
              {formatPackCountNoun(ontologyConceptsCount, cardCopy.activeTermSingular, cardCopy.activeTermPlural, isFr)}
            </span>
          )}
          {workflowsCount > 0 && (
            <span>
              <OrciaIcon name="menuProcesses" /> <strong>{workflowsCount}</strong>{" "}
              {formatPackCountNoun(workflowsCount, cardCopy.processSingular, cardCopy.processPlural, isFr)}
            </span>
          )}
          {(ws.finopsCostUsd ?? 0) > 0 && (
            <span><OrciaIcon name="moneyBag" /> <strong>{formatCurrency(ws.finopsCostUsd ?? 0, resolvedLocale)}</strong></span>
          )}
        </div>
      ) : (
        <div style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>
          {cardCopy.noSourcesOrUsage}
        </div>
      )}

      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center", paddingTop: "4px" }}>
        <select
          data-testid={`workspace-card-phase-select-${ws.workspaceId}`}
          aria-label={cardCopy.phaseSelectAriaLabel}
          value={ws.lifecyclePhase}
          onChange={(e) => {
            const nextPhase = e.target.value as ProductLifecyclePhaseType;
            void Promise.resolve(onUpdateWorkspacePhase(ws.workspaceId, nextPhase))
              .then(() => onMarkAutosaved(ws.workspaceId))
              .catch((err: unknown) => {
                onFeedback(`⚠️ ${formatRfc9457ErrorToBanner(err, resolvedLocale, cardCopy.phaseErrorContext).fullText}`);
              });
          }}
          style={{ ...inputStyle, fontSize: "11px", padding: "4px 8px" }}
        >
          <option value="BUILD">{cardCopy.phaseBuildOption}</option>
          <option value="RUN">{cardCopy.phaseRunOption}</option>
          <option value="MIGRATION">{cardCopy.phaseMigrationOption}</option>
        </select>

        <select
          data-testid={`workspace-card-visibility-select-${ws.workspaceId}`}
          aria-label={cardCopy.visibilitySelectAriaLabel}
          value={ws.visibilityMode}
          onChange={(e) => {
            const nextVis = e.target.value as WorkspaceVisibilityMode;
            void Promise.resolve(onUpdateWorkspaceVisibility(ws.workspaceId, nextVis))
              .then(() => onMarkAutosaved(ws.workspaceId))
              .catch((err: unknown) => {
                onFeedback(`⚠️ ${formatRfc9457ErrorToBanner(err, resolvedLocale, cardCopy.visibilityErrorContext).fullText}`);
              });
          }}
          style={{ ...inputStyle, fontSize: "11px", padding: "4px 8px" }}
        >
          <option value="STANDARD">{`${getOrciaIconGlyph("team")} ${cardCopy.visibilityStandard}`}</option>
          <option value="PRIVATE_USER">{`${getOrciaIconGlyph("lock")} ${cardCopy.visibilityPrivate}`}</option>
          <option value="CONFIDENTIAL_RESTRICTED">{`${getOrciaIconGlyph("shield")} ${cardCopy.visibilityConfidential}`}</option>
        </select>

        {ws.visibilityMode === "PRIVATE_USER" && (
          <button
            type="button"
            data-testid={`share-private-workspace-btn-${ws.workspaceId}`}
            onClick={() => {
              void Promise.resolve(onUpdateWorkspaceVisibility(ws.workspaceId, "STANDARD"))
                .then(() => {
                  onMarkAutosaved(ws.workspaceId);
                  onFeedback(formatI18nTemplate(cardCopy.shareSuccessTemplate, { name: ws.name }));
                })
                .catch((err: unknown) => {
                  onFeedback(`⚠️ ${formatRfc9457ErrorToBanner(err, resolvedLocale, cardCopy.shareErrorContext).fullText}`);
                });
            }}
            style={{
              padding: "4px 8px",
              fontSize: "11px",
              fontWeight: 600,
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-action-primary-subtle)",
              color: "var(--color-action-primary)",
              cursor: "pointer",
            }}
          >
            <OrciaIcon name="team" /> {cardCopy.shareWithTeamBtn}
          </button>
        )}
      </div>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "8px",
          justifyContent: "space-between",
          alignItems: "center",
          borderTop: "1px solid var(--color-border-subtle)",
          paddingTop: "8px",
        }}
      >
        <button
          type="button"
          data-testid={`select-active-workspace-btn-${ws.workspaceId}`}
          onClick={() => onSelectWorkspace(ws.workspaceId)}
          style={{
            padding: "5px 10px",
            fontSize: "11px",
            fontWeight: 600,
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: isSelected ? "var(--color-action-primary)" : "var(--color-bg-elevated)",
            color: isSelected ? "var(--color-primary-foreground)" : "var(--color-text-primary)",
            cursor: "pointer",
          }}
        >
          <OrciaIcon name="target" /> {cardCopy.workInSpaceBtn}
        </button>
        <div style={{ display: "flex", gap: "6px" }}>
          <button
            type="button"
            data-testid={`workspace-open-assistant-btn-${ws.workspaceId}`}
            onClick={() => onNavigateToRoute("/assistant")}
            style={{ padding: "4px 8px", fontSize: "11px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", backgroundColor: "var(--color-surface-card)", cursor: "pointer" }}
          >
            <OrciaIcon name="menuAssistant" /> {cardCopy.openAssistantBtn}
          </button>
          <button
            type="button"
            data-testid={`workspace-open-processes-btn-${ws.workspaceId}`}
            onClick={() => onNavigateToRoute("/processes")}
            style={{ padding: "4px 8px", fontSize: "11px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", backgroundColor: "var(--color-surface-card)", cursor: "pointer" }}
          >
            <OrciaIcon name="menuProcesses" /> {cardCopy.launchProcessBtn}
          </button>
        </div>
      </div>
    </div>
  );
}
