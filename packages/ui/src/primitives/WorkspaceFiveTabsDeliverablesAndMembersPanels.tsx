import React from "react";
import type {
  RebasedChunkItem,
  WorkspaceDeliverableItem,
  WorkspaceFiveTabsLabels,
} from "./WorkspaceFiveTabsAndExternalRebaseView";
import {
  sanitizeUiDestinationUri,
  sanitizeUiWorkspaceSlug,
} from "./WorkspaceFiveTabsPanels";

export interface DeliverablesTabPanelProps {
  readonly workspaceSlug: string;
  readonly defaultArtifactDestinationUri: string;
  readonly deliverables?: readonly WorkspaceDeliverableItem[];
  readonly rebasedChunks: readonly RebasedChunkItem[];
  readonly deliverablesTabSlot?: React.ReactNode;
  readonly labels: WorkspaceFiveTabsLabels;
}

export const DeliverablesTabPanel: React.FC<DeliverablesTabPanelProps> = ({
  workspaceSlug,
  defaultArtifactDestinationUri,
  deliverables = [],
  rebasedChunks,
  deliverablesTabSlot,
  labels,
}) => {
  const safeUri = sanitizeUiDestinationUri(defaultArtifactDestinationUri, workspaceSlug);
  const hasAnyDeliverables = deliverables.length > 0 || rebasedChunks.length > 0;

  return (
    <div
      role="tabpanel"
      aria-labelledby="workspace-tab-DELIVERABLES_ARTIFACTS" // pragma: allowlist secret
      data-testid="workspace-deliverables-panel"
      className="space-y-3 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
    >
      <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
        {labels.tabDeliverablesArtifacts}
      </h3>

      <div
        data-testid="workspace-deliverables-destination"
        className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2.5 text-xs"
      >
        <span className="font-medium">{labels.defaultDestinationTitle} </span>
        <code className="font-mono">{safeUri}</code>
      </div>

      {deliverablesTabSlot ?? null}

      {deliverables.length > 0 && (
        <div className="space-y-1.5">
          {labels.deliverablesCatalogTitle && (
            <h4 className="text-xs font-semibold text-[var(--orcia-text-secondary)]">
              {labels.deliverablesCatalogTitle}
            </h4>
          )}
          <ul data-testid="workspace-deliverables-list" className="space-y-1.5">
            {deliverables.map((item) => (
              <li
                key={item.deliverableId}
                data-testid={`workspace-deliverable-item-${item.deliverableId}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2 text-xs"
              >
                <div className="min-w-0">
                  <div className="font-medium">{item.title}</div>
                  <code className="font-mono text-[11px] text-[var(--orcia-text-secondary)]">
                    {sanitizeUiDestinationUri(item.casUri, workspaceSlug)}
                  </code>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="rounded border border-[var(--orcia-border-subtle)] px-2 py-0.5 font-mono text-[11px]">
                    {item.versionLabel}
                  </span>
                  <span className="rounded border border-[var(--orcia-border-subtle)] px-2 py-0.5 text-[11px]">
                    {item.status}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {rebasedChunks.length > 0 && (
        <div
          data-testid="workspace-external-rebase-section"
          className="space-y-1.5 border-t border-[var(--orcia-border-subtle)] pt-2"
        >
          <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
            {labels.externalRebaseTitle}
          </h4>
          <p className="text-xs text-[var(--orcia-text-secondary)]">
            {labels.supersededMemlogNotice}
          </p>
          <ul className="space-y-1.5">
            {rebasedChunks.map((chunk) => (
              <li
                key={chunk.chunkKey}
                data-testid={`rebased-chunk-${chunk.chunkKey}`}
                className="flex items-center justify-between rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2 text-xs"
              >
                <span className="font-medium">{chunk.sectionTitle}</span>
                {chunk.status === "HUMAN_AMENDED_EXTERNAL" && (
                  <span
                    data-testid={`human-amended-badge-${chunk.chunkKey}`}
                    className="rounded bg-[var(--orcia-surface-secondary)] px-2 py-0.5 font-mono text-[11px]"
                  >
                    {labels.humanAmendedBadge}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!hasAnyDeliverables && !deliverablesTabSlot && (
        <p
          data-testid="workspace-deliverables-empty-state"
          className="text-xs text-[var(--orcia-text-secondary)]"
        >
          {labels.emptyDeliverablesText ?? labels.externalRebaseTitle}
        </p>
      )}
    </div>
  );
};

export interface MembersTeamTabPanelProps {
  readonly workspaceSlug: string;
  readonly workspaceName?: string;
  readonly ownerOrgUnitName?: string | null;
  readonly visibilityLabel?: string;
  readonly effectiveRoleLabel?: string;
  readonly labels: WorkspaceFiveTabsLabels;
  readonly membersTabSlot?: React.ReactNode;
}

export const MembersTeamTabPanel: React.FC<MembersTeamTabPanelProps> = ({
  workspaceSlug,
  workspaceName,
  ownerOrgUnitName,
  visibilityLabel,
  effectiveRoleLabel,
  labels,
  membersTabSlot,
}) => (
  <div
    role="tabpanel"
    aria-labelledby="workspace-tab-MEMBERS_TEAM"
    data-testid="workspace-members-panel"
    className="space-y-3 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
  >
    <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
      {labels.tabMembersTeam}
    </h3>
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 text-xs">
      <div className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2.5">
        <div className="text-[11px] text-[var(--orcia-text-secondary)]">
          {labels.teamBillingLabel ?? labels.tabMembersTeam}
        </div>
        <strong>
          {ownerOrgUnitName || workspaceName || sanitizeUiWorkspaceSlug(workspaceSlug, workspaceName)}
        </strong>
      </div>
      <div className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2.5">
        <div className="text-[11px] text-[var(--orcia-text-secondary)]">
          {labels.visibilityLabel ?? "—"}
        </div>
        <strong>{visibilityLabel ?? "—"}</strong>
      </div>
      <div className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2.5">
        <div className="text-[11px] text-[var(--orcia-text-secondary)]">
          {labels.roleLabel ?? "—"}
        </div>
        <strong>{effectiveRoleLabel ?? "—"}</strong>
      </div>
    </div>
    {labels.membersAccessHint && (
      <p className="text-xs text-[var(--orcia-text-secondary)]">{labels.membersAccessHint}</p>
    )}
    {membersTabSlot ?? null}
  </div>
);
