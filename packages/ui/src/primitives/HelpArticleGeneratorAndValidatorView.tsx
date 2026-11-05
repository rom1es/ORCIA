import type { FC } from "react";

export interface UiHelpValidationSummary {
  articleId: string;
  lang: "fr" | "en";
  passed: boolean;
  boundRoutesValid: boolean;
  uiComponentsAndSectionsValid: boolean;
  glossaryAndZeroSecretValid: boolean;
  elapsedMs: number;
  violations: string[];
}

export interface HelpArticleGeneratorAndValidatorLabels {
  heading: string;
  triggerRegimeLabel: string;
  stagedRegimeBadge: string;
  autonomousRegimeBadge: string;
  validationChecksHeading: string;
  checkBoundRoutesLabel: string;
  checkUiComponentsSectionsLabel: string;
  checkGlossaryZeroSecretLabel: string;
  passedBadge: string;
  failedBadge: string;
  hotAttachmentHeading: string;
  authorityReferenceBadge: string;
  generateAndAttachCta: string;
}

export interface HelpArticleGeneratorAndValidatorViewProps {
  articleId: string;
  version: string;
  packId: string;
  triggerRegime: "STAGED_HUMAN_REVIEW" | "AUTONOMOUS_CONTRACT";
  boundRoutes: string[];
  validationFr: UiHelpValidationSummary;
  validationEn: UiHelpValidationSummary;
  invalidatedRedisKeys: string[];
  exportedGitPaths: string[];
  hotAttachElapsedMs: number;
  labels: HelpArticleGeneratorAndValidatorLabels;
  onGenerateAndAttach?: () => void;
}

export const HelpArticleGeneratorAndValidatorView: FC<
  HelpArticleGeneratorAndValidatorViewProps
> = ({
  articleId,
  version,
  packId,
  triggerRegime,
  boundRoutes,
  validationFr,
  validationEn,
  invalidatedRedisKeys,
  exportedGitPaths,
  hotAttachElapsedMs,
  labels,
  onGenerateAndAttach,
}) => {
  const allValid = validationFr.passed && validationEn.passed;

  return (
    <section
      data-testid="help-article-generator-validator-view"
      className="flex flex-col gap-4 rounded-xl border p-5"
      style={{
        backgroundColor: "var(--color-surface-elevated)",
        borderColor: "var(--color-border-subtle)",
        color: "var(--color-text-primary)",
      }}
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b pb-3">
        <div>
          <h2 className="text-lg font-semibold">{labels.heading}</h2>
          <p
            className="text-xs font-mono"
            style={{ color: "var(--color-text-secondary)" }}
            data-testid="help-article-meta"
          >
            {articleId}@{version} · {packId}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            data-testid="help-authority-reference-badge"
            className="rounded px-2 py-0.5 text-xs font-medium"
            style={{
              backgroundColor: "var(--color-surface-muted)",
              color: "var(--color-accent-primary)",
            }}
          >
            {labels.authorityReferenceBadge}
          </span>
          <span
            data-testid="help-trigger-regime-badge"
            className="rounded px-2 py-0.5 text-xs font-semibold"
            style={{
              backgroundColor: "var(--color-surface-muted)",
              color: "var(--color-text-primary)",
            }}
          >
            {triggerRegime === "STAGED_HUMAN_REVIEW"
              ? labels.stagedRegimeBadge
              : labels.autonomousRegimeBadge}
          </span>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {[validationFr, validationEn].map((val) => (
          <div
            key={val.lang}
            data-testid={`help-validation-card-${val.lang}`}
            className="rounded-lg border p-3 text-xs"
            style={{
              backgroundColor: "var(--color-surface-base)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div className="mb-2 flex items-center justify-between font-semibold">
              <span>
                {labels.validationChecksHeading} ({val.lang.toUpperCase()}) · {val.elapsedMs} ms
              </span>
              <span
                data-testid={`help-validation-status-${val.lang}`}
                style={{
                  color: val.passed ? "var(--color-status-success)" : "var(--color-status-danger)",
                }}
              >
                {val.passed ? labels.passedBadge : labels.failedBadge}
              </span>
            </div>
            <ul className="space-y-1" style={{ color: "var(--color-text-secondary)" }}>
              <li data-testid={`check-routes-${val.lang}`}>
                {val.boundRoutesValid ? "✓" : "✗"} {labels.checkBoundRoutesLabel}
              </li>
              <li data-testid={`check-ui-sections-${val.lang}`}>
                {val.uiComponentsAndSectionsValid ? "✓" : "✗"}{" "}
                {labels.checkUiComponentsSectionsLabel}
              </li>
              <li data-testid={`check-glossary-secret-${val.lang}`}>
                {val.glossaryAndZeroSecretValid ? "✓" : "✗"} {labels.checkGlossaryZeroSecretLabel}
              </li>
            </ul>
          </div>
        ))}
      </div>

      <div
        className="rounded-lg border p-3 text-xs"
        style={{
          backgroundColor: "var(--color-surface-base)",
          borderColor: "var(--color-border-subtle)",
        }}
      >
        <div className="mb-1 flex items-center justify-between font-semibold">
          <span>{labels.hotAttachmentHeading}</span>
          <span data-testid="hot-attach-elapsed-ms" className="font-mono">
            {hotAttachElapsedMs} ms
          </span>
        </div>
        <p className="font-mono" data-testid="help-bound-routes">
          {boundRoutes.join(", ")}
        </p>
        <p
          className="mt-1 font-mono"
          style={{ color: "var(--color-text-secondary)" }}
          data-testid="help-exported-git-paths"
        >
          {exportedGitPaths.join(" | ")}
        </p>
        <p
          className="mt-1 font-mono"
          style={{ color: "var(--color-text-secondary)" }}
          data-testid="help-invalidated-redis-keys"
        >
          {invalidatedRedisKeys.join(", ")}
        </p>
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          data-testid="generate-and-attach-help-btn"
          disabled={!allValid && !onGenerateAndAttach}
          onClick={() => onGenerateAndAttach?.()}
          className="rounded-md px-3 py-1.5 text-xs font-semibold disabled:opacity-40"
          style={{
            backgroundColor: "var(--color-accent-primary)",
            color: "var(--color-surface-elevated)",
          }}
        >
          {labels.generateAndAttachCta}
        </button>
      </div>
    </section>
  );
};
