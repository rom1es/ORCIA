import React from "react";
import type {
  ExceptionWaiverItem,
  RebasedChunkItem,
  WorkspaceFiveTabsLabels,
  WorkspaceSourceItem,
} from "./WorkspaceFiveTabsAndExternalRebaseView";

const TECHNICAL_UUID_RE =
  /^(?:personal-)?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const EMBEDDED_PERSONAL_UUID_RE =
  /personal-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi;

export function sanitizeUiWorkspaceSlug(slug: string, workspaceName?: string): string {
  const trimmed = slug.trim();
  if (!trimmed || TECHNICAL_UUID_RE.test(trimmed)) {
    const cleanName = (workspaceName ?? "").trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
    return cleanName.length > 0 ? cleanName : "ws";
  }
  return trimmed;
}

export function sanitizeUiDestinationUri(uri: string, safeSlug: string): string {
  return uri.replace(EMBEDDED_PERSONAL_UUID_RE, safeSlug);
}

export interface WaiversAndRebasePanelProps {
  readonly workspaceSlug: string;
  readonly defaultArtifactDestinationUri: string;
  readonly sources: readonly WorkspaceSourceItem[];
  readonly activeWaivers: readonly ExceptionWaiverItem[];
  readonly rebasedChunks: readonly RebasedChunkItem[];
  readonly labels: WorkspaceFiveTabsLabels;
  readonly submitting?: boolean;
  readonly onRegisterWaiver?: (sourceUri: string, conflictRuleId: string) => void;
}

export const WaiversAndRebasePanel: React.FC<WaiversAndRebasePanelProps> = ({
  workspaceSlug,
  defaultArtifactDestinationUri,
  sources,
  activeWaivers,
  rebasedChunks,
  labels,
  submitting = false,
  onRegisterWaiver,
}) => (
  <div
    data-testid="workspace-waivers-and-rebase-panel"
    className="space-y-3 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
  >
    <div>
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
        {labels.waiverSectionTitle}
      </h3>
      <p
        data-testid="inviolable-enterprise-lock-notice"
        className="mb-2 text-xs text-[var(--orcia-status-warning)]"
      >
        {labels.inviolableEnterpriseLockNotice}
      </p>
      {onRegisterWaiver &&
        !sources.some((s) => s.freshnessStatus === "STALE_WARNING") && (
          <div className="mb-2">
            <button
              type="button"
              data-testid="register-waiver-btn-workspace-default"
              disabled={submitting}
              aria-busy={submitting}
              onClick={() =>
                onRegisterWaiver(
                  defaultArtifactDestinationUri ||
                    `orcia://workspaces/${workspaceSlug}/sources/default`,
                  "RULE_FRESHNESS_DRIFT",
                )
              }
              className="rounded bg-[var(--orcia-action-primary)] px-2.5 py-1 text-[11px] font-medium text-[var(--orcia-text-on-action)] disabled:opacity-60"
            >
              {labels.registerWaiverCta}
            </button>
          </div>
        )}
      <ul className="space-y-1.5">
        {activeWaivers.map((w) => (
          <li
            key={w.waiverId}
            data-testid={`waiver-item-${w.waiverId}`}
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2 text-xs"
          >
            <div className="flex items-center justify-between">
              <code className="font-mono">{w.conflictRuleId}</code>
              <span className="font-mono text-[11px]">{w.normLevel}</span>
            </div>
            <div className="text-[11px] text-[var(--orcia-text-secondary)]">
              {w.reason}
            </div>
          </li>
        ))}
      </ul>
    </div>

    <div className="border-t border-[var(--orcia-border-subtle)] pt-2">
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
        {labels.externalRebaseTitle}
      </h3>
      <p className="mb-2 font-mono text-[11px] text-[var(--orcia-text-secondary)]">
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
  </div>
);

export interface SourcesTabListPanelProps {
  readonly sources: readonly WorkspaceSourceItem[];
  readonly labels: WorkspaceFiveTabsLabels;
  readonly submitting?: boolean;
  readonly onRegisterWaiver?: (sourceUri: string, conflictRuleId: string) => void;
}

export const SourcesTabListPanel: React.FC<SourcesTabListPanelProps> = ({
  sources,
  labels,
  submitting = false,
  onRegisterWaiver,
}) => (
  <div
    data-testid="workspace-sources-panel"
    className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
  >
    <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
      {labels.tabDocumentsSources}
    </h3>
    <ul className="space-y-2">
      {sources.map((src) => (
        <li
          key={src.sourceId}
          data-testid={`workspace-source-${src.sourceId}`}
          className="flex flex-wrap items-center justify-between gap-2 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2 text-xs"
        >
          <div>
            <div className="font-medium">{src.title}</div>
            <code className="font-mono text-[11px] text-[var(--orcia-text-secondary)]">
              {src.uri}
            </code>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="rounded border border-[var(--orcia-border-subtle)] px-2 py-0.5 text-[11px]">
              {src.authorityRole === "REFERENCE"
                ? labels.roleReferenceBadge
                : labels.roleActiveBadge}
            </span>
            <span className="rounded border border-[var(--orcia-border-subtle)] px-2 py-0.5 text-[11px]">
              {src.accessMode === "READ_ONLY"
                ? labels.modeReadOnlyBadge
                : labels.modeReadWriteBadge}
            </span>
            {src.freshnessStatus === "STALE_WARNING" && onRegisterWaiver && (
              <button
                type="button"
                data-testid={`register-waiver-btn-${src.sourceId}`}
                disabled={submitting}
                aria-busy={submitting}
                onClick={() => onRegisterWaiver(src.uri, "RULE_FRESHNESS_DRIFT")}
                className="rounded bg-[var(--orcia-action-primary)] px-2 py-0.5 text-[11px] text-[var(--orcia-text-on-action)] disabled:opacity-60"
              >
                {labels.registerWaiverCta}
              </button>
            )}
          </div>
        </li>
      ))}
    </ul>
  </div>
);

export interface DeliverablesTabPanelProps {
  readonly defaultArtifactDestinationUri: string;
  readonly rebasedChunks: readonly RebasedChunkItem[];
  readonly labels: WorkspaceFiveTabsLabels;
}

export const DeliverablesTabPanel: React.FC<DeliverablesTabPanelProps> = ({
  defaultArtifactDestinationUri,
  rebasedChunks,
  labels,
}) => (
  <div
    role="tabpanel"
    aria-labelledby="workspace-tab-DELIVERABLES_ARTIFACTS" // pragma: allowlist secret
    data-testid="workspace-deliverables-panel"
    className="space-y-3 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
  >
    <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
      {labels.tabDeliverablesArtifacts}
    </h3>
    <div className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2.5 text-xs">
      <span className="font-medium">{labels.defaultDestinationTitle} </span>
      <code className="font-mono">{sanitizeUiDestinationUri(defaultArtifactDestinationUri, "ws")}</code>
    </div>
    <p className="text-xs text-[var(--orcia-text-secondary)]">{labels.supersededMemlogNotice}</p>
    {rebasedChunks.length === 0 ? (
      <p className="text-xs text-[var(--orcia-text-secondary)]">
        {labels.emptyDeliverablesText ?? labels.externalRebaseTitle}
      </p>
    ) : (
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
    )}
  </div>
);

export interface MembersTeamTabPanelProps {
  readonly workspaceSlug: string;
  readonly workspaceName?: string;
  readonly ownerOrgUnitName?: string | null;
  readonly visibilityLabel?: string;
  readonly effectiveRoleLabel?: string;
  readonly labels: WorkspaceFiveTabsLabels;
}

export const MembersTeamTabPanel: React.FC<MembersTeamTabPanelProps> = ({
  workspaceSlug,
  workspaceName,
  ownerOrgUnitName,
  visibilityLabel,
  effectiveRoleLabel,
  labels,
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
        <strong>{ownerOrgUnitName || workspaceName || sanitizeUiWorkspaceSlug(workspaceSlug, workspaceName)}</strong>
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
  </div>
);
