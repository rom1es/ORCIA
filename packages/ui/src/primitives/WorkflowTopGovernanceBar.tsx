import type { ReactNode } from "react";

export type StudioLifecycleTabKey =
  | "PUBLISHED"
  | "DRAFT"
  | "TRASH"
  | "ACTIVE_RUNS"
  | "PAUSED_ARBITRATION";

export interface StudioLifecycleTabCount {
  readonly tab: StudioLifecycleTabKey;
  readonly label: string;
  readonly count: number;
}

export interface WorkflowTopGovernanceBarProps {
  readonly workflowKey: string;
  readonly version: string;
  readonly lifecycleStatus: StudioLifecycleTabKey;
  readonly prePromptSha256: string;
  readonly requiredParams: readonly string[];
  readonly requiredMarkdownSections: readonly string[];
  readonly triggers: readonly string[];
  readonly activeTab: StudioLifecycleTabKey;
  readonly tabCounts: readonly StudioLifecycleTabCount[];
  readonly onSelectTab: (tab: StudioLifecycleTabKey) => void;
  readonly onForkDraft?: () => void;
  readonly onOpenPrePrompt?: () => void;
  readonly onOpenContract?: () => void;
  readonly onOpenTriggers?: () => void;
  readonly onRunDryRunTest?: () => void;
  readonly onPublishDraft?: () => void;
  readonly labels: {
    readonly prePromptButton: string;
    readonly contractButton: string;
    readonly triggersButton: string;
    readonly dryRunButton: string;
    readonly forkButton: string;
    readonly publishButton: string;
    readonly readOnlyPublishedHint: string;
  };
  readonly extraActions?: ReactNode;
}

/**
 * Barre supérieure de gouvernance du Studio Visuel (Story 8.5 / UX-DR18) :
 * - 5 onglets de cycle de vie (Publiés, Brouillons, Corbeille, En cours, En attente d'arbitrage)
 * - Boutons Pré-prompt IA (sha256), Contrat ({p_1..p_n} + sections Markdown), Déclencheurs, ▷ Tester (Dry-run)
 * - Fork immuable SemVer (vX.Y.Z -> vX.Y+1.0-draft) si PUBLISHED, ou Publication si DRAFT.
 */
export function WorkflowTopGovernanceBar({
  workflowKey,
  version,
  lifecycleStatus,
  prePromptSha256,
  requiredParams,
  requiredMarkdownSections,
  triggers,
  activeTab,
  tabCounts,
  onSelectTab,
  onForkDraft,
  onOpenPrePrompt,
  onOpenContract,
  onOpenTriggers,
  onRunDryRunTest,
  onPublishDraft,
  labels,
  extraActions,
}: WorkflowTopGovernanceBarProps) {
  const isPublished = lifecycleStatus === "PUBLISHED";
  const isDraft = lifecycleStatus === "DRAFT";

  return (
    <header
      data-testid="workflow-top-governance-bar"
      className="flex flex-col gap-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-elevated)] p-3"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold text-[var(--color-text-primary)]">
            {workflowKey}
          </span>
          <span
            data-testid="workflow-semver-badge"
            className="rounded bg-[var(--color-surface-canvas)] px-2 py-0.5 font-mono text-xs text-[var(--color-text-secondary)]"
          >
            v{version}
          </span>
          {isPublished ? (
            <span
              data-testid="workflow-readonly-hint"
              className="text-xs text-[var(--color-text-muted)]"
            >
              {labels.readOnlyPublishedHint}
            </span>
          ) : null}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            data-testid="workflow-preprompt-btn"
            onClick={onOpenPrePrompt}
            className="inline-flex items-center gap-1.5 rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-canvas)] px-2.5 py-1 text-xs font-medium text-[var(--color-text-primary)]"
          >
            <span>{labels.prePromptButton}</span>
            <code className="font-mono text-[10px] text-[var(--color-text-muted)]">
              {prePromptSha256.slice(0, 12)}
            </code>
          </button>

          <button
            type="button"
            data-testid="workflow-contract-btn"
            onClick={onOpenContract}
            className="inline-flex items-center gap-1.5 rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-canvas)] px-2.5 py-1 text-xs font-medium text-[var(--color-text-primary)]"
          >
            <span>{labels.contractButton}</span>
            <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
              ({requiredParams.length}p / {requiredMarkdownSections.length}s)
            </span>
          </button>

          <button
            type="button"
            data-testid="workflow-triggers-btn"
            onClick={onOpenTriggers}
            className="inline-flex items-center gap-1.5 rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-canvas)] px-2.5 py-1 text-xs font-medium text-[var(--color-text-primary)]"
          >
            <span>{labels.triggersButton}</span>
            <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
              ({triggers.length})
            </span>
          </button>

          <button
            type="button"
            data-testid="workflow-dryrun-btn"
            onClick={onRunDryRunTest}
            className="inline-flex items-center gap-1.5 rounded border border-[var(--color-brand-primary)] bg-[var(--color-surface-canvas)] px-2.5 py-1 text-xs font-semibold text-[var(--color-brand-primary)]"
          >
            {labels.dryRunButton}
          </button>

          {isPublished && onForkDraft ? (
            <button
              type="button"
              data-testid="workflow-fork-btn"
              onClick={onForkDraft}
              className="rounded bg-[var(--color-brand-primary)] px-3 py-1 text-xs font-semibold text-[var(--color-surface-elevated)]"
            >
              {labels.forkButton}
            </button>
          ) : null}

          {isDraft && onPublishDraft ? (
            <button
              type="button"
              data-testid="workflow-publish-btn"
              onClick={onPublishDraft}
              className="rounded bg-[var(--color-status-completed)] px-3 py-1 text-xs font-semibold text-[var(--color-surface-elevated)]"
            >
              {labels.publishButton}
            </button>
          ) : null}

          {extraActions}
        </div>
      </div>

      <nav
        role="tablist"
        aria-label="Workflow lifecycle tabs"
        className="flex flex-wrap items-center gap-1.5 border-t border-[var(--color-border-subtle)] pt-2"
      >
        {tabCounts.map((entry) => {
          const selected = entry.tab === activeTab;
          return (
            <button
              key={entry.tab}
              type="button"
              role="tab"
              aria-selected={selected}
              data-testid={`studio-tab-${entry.tab}`}
              onClick={() => onSelectTab(entry.tab)}
              className={`inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                selected
                  ? "bg-[var(--color-brand-primary)] text-[var(--color-surface-elevated)]"
                  : "bg-[var(--color-surface-canvas)] text-[var(--color-text-secondary)]"
              }`}
            >
              <span>{entry.label}</span>
              <span className="rounded-full bg-[var(--color-surface-elevated)]/20 px-1.5 py-0.2 font-mono text-[10px]">
                {entry.count}
              </span>
            </button>
          );
        })}
      </nav>
    </header>
  );
}
