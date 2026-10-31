import React from "react";

export interface UiCompiledStarlarkMechanism {
  readonly mechanismId: string;
  readonly ruleId: string;
  readonly scriptName: string;
  readonly starlarkCode: string;
  readonly sha256: string;
  readonly explanationFr: string;
  readonly verifiedBadgeFr: string;
  readonly causalBreadcrumb: string;
  readonly selfCorrected: boolean;
  readonly signedAndActive: boolean;
}

export interface UiGlossaryCandidateItem {
  readonly candidateId: string;
  readonly canonicalTerm: string;
  readonly definitionFr: string;
  readonly confidenceScore: number;
  readonly ontologyConflictWarning: string | null;
  readonly preCheckedForInFlowPromotion: boolean;
}

export interface DnaStarlarkAndGlossaryLabels {
  readonly heading: string;
  readonly generateStarlarkCta: string;
  readonly signAndActivateCta: string;
  readonly runtimeZeroTokenBadge: string;
  readonly queueSectionTitle: string;
  readonly inFlowBriefingTitle: string;
  readonly promoteInFlowCheckboxLabel: string;
  readonly promoteSelectedCta: string;
  readonly rejectCandidateCta: string;
}

export interface DnaStarlarkCompilerAndGlossaryLifecycleViewProps {
  readonly mechanism?: UiCompiledStarlarkMechanism | null;
  readonly pendingQueueCandidates: readonly UiGlossaryCandidateItem[];
  readonly top3PrecheckedCandidates: readonly UiGlossaryCandidateItem[];
  readonly labels: DnaStarlarkAndGlossaryLabels;
  readonly onCompileFromNorm?: (ruleId: string) => void;
  readonly onSignAndActivate?: (mechanismId: string) => void;
  readonly onPromoteInFlow?: (candidateIds: readonly string[]) => void;
  readonly onRejectCandidate?: (candidateId: string) => void;
}

export const DnaStarlarkCompilerAndGlossaryLifecycleView: React.FC<
  DnaStarlarkCompilerAndGlossaryLifecycleViewProps
> = ({
  mechanism = null,
  pendingQueueCandidates,
  top3PrecheckedCandidates,
  labels,
  onCompileFromNorm,
  onSignAndActivate,
  onPromoteInFlow,
  onRejectCandidate,
}) => {
  const cappedQueue = pendingQueueCandidates.slice(0, 15);
  const cappedTop3 = top3PrecheckedCandidates.slice(0, 3);

  return (
    <section
      aria-label={labels.heading}
      data-testid="dna-starlark-glossary-view"
      className="space-y-4 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-4 text-[var(--orcia-text-primary)]"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--orcia-border-subtle)] pb-3">
        <div>
          <h2 className="text-base font-semibold">{labels.heading}</h2>
          {mechanism && (
            <p
              data-testid="dna-causal-breadcrumb"
              className="font-mono text-xs text-[var(--orcia-text-secondary)]"
            >
              {mechanism.causalBreadcrumb}
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {mechanism && (
            <span
              data-testid="starlark-verified-badge"
              className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1 text-xs font-medium"
            >
              {mechanism.verifiedBadgeFr}
            </span>
          )}
          <span className="rounded border border-[var(--orcia-border-subtle)] px-2 py-1 font-mono text-[11px] text-[var(--orcia-text-secondary)]">
            {labels.runtimeZeroTokenBadge}
          </span>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {mechanism ? (
          <div
            data-testid="starlark-compiler-panel"
            className="space-y-2 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
          >
            <div className="flex items-center justify-between">
              <code className="font-mono text-xs font-semibold">
                {mechanism.scriptName}
              </code>
              <code className="font-mono text-[11px] text-[var(--orcia-text-secondary)]">
                {mechanism.sha256.slice(0, 12)}
              </code>
            </div>
            <p className="text-xs text-[var(--orcia-text-secondary)]">
              {mechanism.explanationFr}
            </p>
            <pre
              data-testid="starlark-code-preview"
              className="overflow-x-auto rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2 font-mono text-xs"
            >
              {mechanism.starlarkCode}
            </pre>
            <div className="flex flex-wrap gap-2 pt-1">
              {onCompileFromNorm && (
                <button
                  type="button"
                  data-testid="compile-starlark-btn"
                  onClick={() => onCompileFromNorm(mechanism.ruleId)}
                  className="rounded bg-[var(--orcia-surface-primary)] px-3 py-1.5 text-xs font-medium"
                >
                  {labels.generateStarlarkCta}
                </button>
              )}
              {onSignAndActivate && (
                <button
                  type="button"
                  data-testid="sign-activate-starlark-btn"
                  onClick={() => onSignAndActivate(mechanism.mechanismId)}
                  className="rounded bg-[var(--orcia-action-primary)] px-3 py-1.5 text-xs font-medium text-[var(--orcia-text-on-action)]"
                >
                  {labels.signAndActivateCta}
                </button>
              )}
            </div>
          </div>
        ) : (
          <div
            data-testid="dna-starlark-empty-state"
            className="flex flex-col justify-center rounded border border-dashed border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-4 text-xs text-[var(--orcia-text-secondary)]"
          >
            Aucun mécanisme Starlark compilé pour cet Espace. Ajoutez une norme métier pour compiler un contrôle déterministe.
          </div>
        )}

        <div className="space-y-3">
          <div
            data-testid="in-flow-top3-panel"
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
          >
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
                {labels.inFlowBriefingTitle}
              </h3>
              {onPromoteInFlow && (
                <button
                  type="button"
                  data-testid="promote-in-flow-btn"
                  onClick={() =>
                    onPromoteInFlow(cappedTop3.map((c) => c.candidateId))
                  }
                  className="rounded bg-[var(--orcia-action-primary)] px-2.5 py-1 text-xs font-medium text-[var(--orcia-text-on-action)]"
                >
                  {labels.promoteSelectedCta}
                </button>
              )}
            </div>
            <ul className="space-y-1.5">
              {cappedTop3.map((cand) => (
                <li
                  key={cand.candidateId}
                  data-testid={`top3-candidate-${cand.candidateId}`}
                  className="flex items-center justify-between rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2 text-xs"
                >
                  <label className="inline-flex items-center gap-2">
                    <input
                      type="checkbox"
                      defaultChecked={cand.preCheckedForInFlowPromotion}
                      aria-label={`${labels.promoteInFlowCheckboxLabel} ${cand.canonicalTerm}`}
                    />
                    <span className="font-medium">{cand.canonicalTerm}</span>
                  </label>
                  <span className="font-mono text-[11px] text-[var(--orcia-text-secondary)]">
                    {cand.confidenceScore.toFixed(2)}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div
            data-testid="glossary-fifo-queue-panel"
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
          >
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
              {labels.queueSectionTitle} ({cappedQueue.length}/15)
            </h3>
            <ul className="space-y-1.5">
              {cappedQueue.map((cand) => (
                <li
                  key={cand.candidateId}
                  data-testid={`queue-candidate-${cand.candidateId}`}
                  className="flex flex-wrap items-center justify-between gap-2 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2 text-xs"
                >
                  <div>
                    <div className="font-medium">{cand.canonicalTerm}</div>
                    <div className="text-[11px] text-[var(--orcia-text-secondary)]">
                      {cand.definitionFr}
                    </div>
                    {cand.ontologyConflictWarning && (
                      <div
                        data-testid={`conflict-warning-${cand.candidateId}`}
                        className="text-[11px] text-[var(--orcia-status-warning)]"
                      >
                        {cand.ontologyConflictWarning}
                      </div>
                    )}
                  </div>
                  {onRejectCandidate && (
                    <button
                      type="button"
                      data-testid={`reject-candidate-btn-${cand.candidateId}`}
                      onClick={() => onRejectCandidate(cand.candidateId)}
                      className="rounded border border-[var(--orcia-border-subtle)] px-2 py-0.5 text-[11px]"
                    >
                      {labels.rejectCandidateCta}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
};
