import React, { useState } from "react";

export type UiHelpArticleLayer = "BASE" | "PACK" | "WORKSPACE" | "USER";

export interface UiContextualHelpArticleView {
  readonly resourceId: string;
  readonly uri: string;
  readonly title: string;
  readonly version: string;
  readonly lang: "fr" | "en";
  readonly layer: UiHelpArticleLayer;
  readonly packName: string | null;
  readonly boundRoutes: readonly string[];
  readonly summaryWhatFor: string;
  readonly stepByStepItems: readonly string[];
  readonly keyTermsItems: readonly string[];
  readonly faqItems: readonly string[];
  readonly casKey: string;
  readonly sha256: string;
  readonly previousVersion?: string | null;
}

export interface ContextualHelpColumnAndCenterLabels {
  readonly columnHeaderTitle: string;
  readonly centerHeaderTitle: string;
  readonly whatForSectionTitle: string;
  readonly stepByStepAccordionTitle: string;
  readonly keyTermsAccordionTitle: string;
  readonly faqAccordionTitle: string;
  readonly askAssistantOnScreenCta: string;
  readonly rollbackButtonLabel: string;
  readonly rollbackCompletedPrefix: string;
  readonly mergedLayersPrefix: string;
}

export interface ContextualHelpColumnAndCenterProps {
  readonly mode?: "COLUMN_340PX" | "HELP_MENU_CENTER";
  readonly route: string;
  readonly pack: string;
  readonly redisCacheKey: string;
  readonly mergedLayers: readonly UiHelpArticleLayer[];
  readonly article: UiContextualHelpArticleView;
  readonly rollbackAvailable?: boolean;
  readonly isAdmin?: boolean;
  readonly labels: ContextualHelpColumnAndCenterLabels;
  readonly onAskAssistantOnScreen?: (route: string, prefillPrompt: string) => void;
  readonly onRollbackVersion?: (resourceId: string) => void;
}

/**
 * Story 9.5 — Hybrid Contextual Help Column (`❓`, `340px`) & Help Menu Center (`Aide`).
 * Displays the resolved `HELP_ARTICLE` (`catalog_items` + `cas/<sha256>` + Redis `< 10 ms`),
 * 4-layer merge indicator (`AD-14`), 3 accordions, Assistant CTA, and 1-click `⏪ Rollback` (`@v(N-1)`).
 */
export function ContextualHelpColumnAndCenter({
  mode = "COLUMN_340PX",
  route,
  pack,
  redisCacheKey,
  mergedLayers,
  article,
  rollbackAvailable = false,
  isAdmin = false,
  labels,
  onAskAssistantOnScreen,
  onRollbackVersion,
}: ContextualHelpColumnAndCenterProps): React.ReactElement {
  const [openSteps, setOpenSteps] = useState<boolean>(true);
  const [openTerms, setOpenTerms] = useState<boolean>(true);
  const [openFaq, setOpenFaq] = useState<boolean>(false);
  const [rolledBackToVersion, setRolledBackToVersion] = useState<string | null>(
    null,
  );

  const displayVersion = rolledBackToVersion ?? article.version;

  const handleRollback = (): void => {
    const prevVer = article.previousVersion ?? "1.0.0";
    setRolledBackToVersion(prevVer);
    onRollbackVersion?.(article.resourceId);
  };

  return (
    <section
      aria-label={
        mode === "COLUMN_340PX"
          ? labels.columnHeaderTitle
          : labels.centerHeaderTitle
      }
      data-testid="contextual-help-hybrid-panel"
      data-mode={mode}
      className={`${
        mode === "COLUMN_340PX" ? "w-[340px]" : "w-full max-w-4xl"
      } rounded-xl border border-surface-border bg-surface-elevated p-3.5 text-xs text-text-primary space-y-3`}
    >
      {/* Header + Version & CAS Metadata */}
      <div className="border-b border-surface-border pb-2.5 space-y-1">
        <div className="flex items-center justify-between gap-2">
          <span className="font-semibold text-sm">{article.title}</span>
          <span
            data-testid="contextual-help-version-pill"
            className="px-2 py-0.5 rounded-full font-mono text-[11px] bg-surface-secondary border border-surface-border"
          >
            @{displayVersion}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono text-text-secondary">
          <span data-testid="contextual-help-redis-key">{redisCacheKey}</span>
          <span>·</span>
          <span data-testid="contextual-help-cas-key">{article.casKey}</span>
        </div>
        <div
          data-testid="contextual-help-merged-layers"
          className="text-[11px] text-text-secondary"
        >
          {labels.mergedLayersPrefix} {mergedLayers.join(" → ")} ({pack})
        </div>
      </div>

      {/* Summary: "À quoi sert cet écran ?" */}
      <div
        data-testid="contextual-help-what-for-box"
        className="p-2.5 rounded-lg border border-surface-border bg-surface-primary space-y-1"
      >
        <div className="font-semibold text-text-primary">
          {labels.whatForSectionTitle}
        </div>
        <p className="text-text-secondary leading-relaxed">
          {article.summaryWhatFor}
        </p>
      </div>

      {/* Accordion 1: Pas-à-pas */}
      <div className="rounded-lg border border-surface-border overflow-hidden">
        <button
          type="button"
          aria-expanded={openSteps}
          data-testid="help-accordion-steps-btn"
          onClick={() => setOpenSteps((prev) => !prev)}
          className="w-full px-3 py-2 bg-surface-secondary text-left font-semibold flex items-center justify-between"
        >
          <span>{labels.stepByStepAccordionTitle}</span>
          <span>{openSteps ? "▾" : "▸"}</span>
        </button>
        {openSteps && (
          <ol
            data-testid="help-accordion-steps-content"
            className="p-3 space-y-1.5 list-decimal list-inside text-text-secondary bg-surface-primary"
          >
            {article.stepByStepItems.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ol>
        )}
      </div>

      {/* Accordion 2: Termes clés */}
      <div className="rounded-lg border border-surface-border overflow-hidden">
        <button
          type="button"
          aria-expanded={openTerms}
          data-testid="help-accordion-terms-btn"
          onClick={() => setOpenTerms((prev) => !prev)}
          className="w-full px-3 py-2 bg-surface-secondary text-left font-semibold flex items-center justify-between"
        >
          <span>{labels.keyTermsAccordionTitle}</span>
          <span>{openTerms ? "▾" : "▸"}</span>
        </button>
        {openTerms && (
          <ul
            data-testid="help-accordion-terms-content"
            className="p-3 space-y-1.5 list-disc list-inside text-text-secondary bg-surface-primary"
          >
            {article.keyTermsItems.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        )}
      </div>

      {/* Accordion 3: Questions fréquentes */}
      <div className="rounded-lg border border-surface-border overflow-hidden">
        <button
          type="button"
          aria-expanded={openFaq}
          data-testid="help-accordion-faq-btn"
          onClick={() => setOpenFaq((prev) => !prev)}
          className="w-full px-3 py-2 bg-surface-secondary text-left font-semibold flex items-center justify-between"
        >
          <span>{labels.faqAccordionTitle}</span>
          <span>{openFaq ? "▾" : "▸"}</span>
        </button>
        {openFaq && (
          <ul
            data-testid="help-accordion-faq-content"
            className="p-3 space-y-1.5 list-disc list-inside text-text-secondary bg-surface-primary"
          >
            {article.faqItems.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        )}
      </div>

      {/* Admin 1-Click Rollback to @v(N-1) */}
      {isAdmin && rollbackAvailable && (
        <div className="pt-1 flex items-center justify-between gap-2">
          <button
            type="button"
            data-testid="contextual-help-rollback-btn"
            onClick={handleRollback}
            className="px-2.5 py-1 rounded border border-surface-border bg-surface-secondary font-medium text-text-primary"
          >
            {labels.rollbackButtonLabel} (@{article.previousVersion ?? "1.0.0"})
          </button>
          {rolledBackToVersion !== null && (
            <span
              data-testid="contextual-help-rollback-banner"
              className="font-mono text-[11px] text-status-success"
            >
              {labels.rollbackCompletedPrefix} @{rolledBackToVersion}
            </span>
          )}
        </div>
      )}

      {/* Footer CTA: Ask Mon Assistant about this screen */}
      <div className="pt-2 border-t border-surface-border">
        <button
          type="button"
          data-testid="contextual-help-ask-assistant-btn"
          onClick={() =>
            onAskAssistantOnScreen?.(
              route,
              `Explique-moi comment utiliser l'écran ${route} (${article.title})`,
            )
          }
          className="w-full py-1.5 px-3 rounded-lg bg-brand-primary text-surface-elevated font-medium text-center"
        >
          {labels.askAssistantOnScreenCta}
        </button>
      </div>
    </section>
  );
}
