import React from "react";
import { AutonomousExecutionBadge, type AutonomousExecutionBadgeLabels } from "./AutonomousExecutionBadge";
import type {
  ContextualHelpColumnAndCenterLabels,
  UiContextualHelpArticleView,
  UiHelpArticleLayer,
} from "./ContextualHelpTypes";

const HELP_LAYER_LABELS_FR: Record<UiHelpArticleLayer, string> = {
  BASE: "Base",
  PACK: "Pack",
  WORKSPACE: "Espace",
  USER: "Utilisateur",
};

const HELP_LAYER_LABELS_EN: Record<UiHelpArticleLayer, string> = {
  BASE: "Base",
  PACK: "Pack",
  WORKSPACE: "Workspace",
  USER: "User",
};

export function HelpArticleHeaderBlock({
  article,
  pack,
  redisCacheKey,
  mergedLayers,
  rollbackAvailable,
  showTechDetails,
  rolledBackToVersion,
  onSetRolledBack,
  labels,
  autonomousBadgeLabels,
  onRollbackVersion,
  onInvalidateAndRestoreAutonomousHelp,
  titleAsHeading,
}: {
  readonly article: UiContextualHelpArticleView;
  readonly pack: string;
  readonly redisCacheKey: string;
  readonly mergedLayers: readonly UiHelpArticleLayer[];
  readonly rollbackAvailable: boolean;
  readonly showTechDetails: boolean;
  readonly rolledBackToVersion: string | null;
  readonly onSetRolledBack: (v: string) => void;
  readonly labels: ContextualHelpColumnAndCenterLabels;
  readonly autonomousBadgeLabels?: AutonomousExecutionBadgeLabels;
  readonly onRollbackVersion?: (resourceId: string) => void;
  readonly onInvalidateAndRestoreAutonomousHelp?: (runId: string, resourceId: string) => void;
  readonly titleAsHeading?: boolean;
}): React.ReactElement {
  const displayVersion = rolledBackToVersion ?? article.version;
  const isEn = article.lang === "en";

  return (
    <div className="border-b border-surface-border pb-2.5 space-y-2">
      {titleAsHeading ? (
        <h3 className="font-semibold text-sm text-text-primary m-0">{article.title}</h3>
      ) : (
        <span className="font-semibold text-sm block">{article.title}</span>
      )}
      {article.isAutonomousGenerated && autonomousBadgeLabels && (
        <AutonomousExecutionBadge
          testId="contextual-help-autonomous-badge"
          runId={article.autonomousRunId}
          triggerLabel={article.triggerLabel}
          contractLabel={article.contractLabel}
          canEmergencyStop={false}
          canInvalidateAndRestore={Boolean(article.autonomousRunId || rollbackAvailable)}
          compact
          labels={autonomousBadgeLabels}
          onInvalidateAndRestore={(rid) => {
            onSetRolledBack(article.previousVersion ?? "1.0.0");
            if (onInvalidateAndRestoreAutonomousHelp) {
              onInvalidateAndRestoreAutonomousHelp(rid, article.resourceId);
            } else {
              onRollbackVersion?.(article.resourceId);
            }
          }}
        />
      )}
      {showTechDetails && Boolean(displayVersion || mergedLayers.length > 0 || article.casKey) && (
        <details
          data-testid="contextual-help-technical-details"
          className="rounded border border-surface-border bg-surface-secondary px-2.5 py-1.5 text-[11px] text-text-secondary"
        >
          <summary className="cursor-pointer font-medium">
            {labels.technicalDetailsTitle ?? (isEn ? "Technical details" : "Détails techniques")}
          </summary>
          <div className="mt-1.5 space-y-1">
            {displayVersion && (
              <div className="flex items-center justify-between gap-2">
                <span>Version</span>
                <span
                  data-testid="contextual-help-version-pill"
                  className="px-2 py-0.5 rounded-full font-mono text-[11px] bg-surface-primary border border-surface-border"
                >
                  v{displayVersion}
                </span>
              </div>
            )}
            {mergedLayers.length > 0 && (
              <div data-testid="contextual-help-merged-layers">
                {labels.mergedLayersPrefix}{" "}
                {mergedLayers
                  .map((layer) => (isEn ? HELP_LAYER_LABELS_EN[layer] : HELP_LAYER_LABELS_FR[layer]) ?? layer)
                  .join(" / ")}{" "}
                ({pack})
              </div>
            )}
            <div className="hidden" aria-hidden="true">
              <span data-testid="contextual-help-redis-key">{redisCacheKey}</span>
              <span data-testid="contextual-help-cas-key">{article.casKey}</span>
            </div>
          </div>
        </details>
      )}
    </div>
  );
}

export function HelpCoreNarrativeBlocks({
  article,
  labels,
  showStepsBlock,
}: {
  readonly article: UiContextualHelpArticleView;
  readonly labels: ContextualHelpColumnAndCenterLabels;
  readonly showStepsBlock: boolean;
}): React.ReactElement {
  const isEn = article.lang === "en";
  const stepsCount = article.stepByStepItems.length;
  const pitfalls = article.commonPitfallsItems ?? [];
  const stepsHeading = `${labels.stepsBlockPrefix ?? (isEn ? "In" : "En")} ${stepsCount} ${
    labels.stepsBlockSuffix ?? (isEn ? "steps" : "gestes")
  }`;

  return (
    <>
      <div
        data-testid="contextual-help-what-for-box"
        className="p-2.5 rounded-lg border border-surface-border bg-surface-primary space-y-1"
      >
        <div className="font-semibold text-text-primary">{labels.whatForSectionTitle}</div>
        <p className="text-text-secondary leading-relaxed">{article.summaryWhatFor}</p>
      </div>

      {showStepsBlock && stepsCount > 0 && (
        <div
          data-testid="contextual-help-steps-box"
          className="p-2.5 rounded-lg border border-surface-border bg-surface-primary space-y-1.5"
        >
          <div className="text-[11px] font-bold uppercase tracking-wide text-text-primary">
            {stepsHeading}
          </div>
          <ol
            data-testid="help-accordion-steps-content"
            className="list-decimal space-y-1.5 pl-4 text-text-secondary leading-relaxed"
          >
            {article.stepByStepItems.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ol>
        </div>
      )}

      {article.realExampleText && (
        <div
          data-testid="contextual-help-real-example-box"
          className="p-2.5 rounded-lg border space-y-1"
          style={{
            backgroundColor: "var(--color-help-example-bg)",
            borderColor: "var(--color-help-example-border)",
          }}
        >
          <div
            className="text-[11px] font-bold uppercase tracking-wide"
            style={{ color: "var(--color-help-example-title)" }}
          >
            {labels.realExampleTitle ?? (isEn ? "A real example" : "Un exemple réel")}
          </div>
          <p className="leading-relaxed" style={{ color: "var(--color-help-example-text)" }}>
            {article.realExampleText}
          </p>
        </div>
      )}

      {pitfalls.length > 0 && (
        <div
          data-testid="contextual-help-common-pitfalls-box"
          className="p-2.5 rounded-lg border border-surface-border bg-surface-primary space-y-1.5"
        >
          <div className="text-[11px] font-bold uppercase tracking-wide text-text-primary">
            {labels.commonPitfallsTitle ?? (isEn ? "Common pitfalls" : "Ce qui coince souvent")}
          </div>
          <ul className="list-disc space-y-1.5 pl-4 text-text-secondary leading-relaxed">
            {pitfalls.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
