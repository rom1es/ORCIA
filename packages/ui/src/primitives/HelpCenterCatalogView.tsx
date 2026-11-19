import React, { useState } from "react";
import {
  HelpArticleHeaderBlock,
  HelpCoreNarrativeBlocks,
} from "./ContextualHelpSharedBlocks";
import {
  HelpAccordionSection,
  HelpFooterActions,
} from "./ContextualHelpSectionsAndFooter";
import type { ContextualHelpColumnAndCenterProps } from "./ContextualHelpTypes";

/**
 * `/help` (`HELP_MENU_CENTER`) — Help Center catalog view displaying the 4 DESIGN.md blocks,
 * non-duplicated interactive accordions (`steps`, `terms`, `faq`), and admin-gated metadata.
 */
export function HelpCenterCatalogView({
  route,
  pack,
  redisCacheKey,
  mergedLayers,
  article,
  activeSectionId = null,
  rollbackAvailable = false,
  isAdmin = false,
  showTechnicalMetadata,
  askAssistantPrefill,
  labels,
  autonomousBadgeLabels,
  onAskAssistantOnScreen,
  onRollbackVersion,
  onInvalidateAndRestoreAutonomousHelp,
}: ContextualHelpColumnAndCenterProps): React.ReactElement {
  const [openSteps, setOpenSteps] = useState<boolean>(false);
  const [openTerms, setOpenTerms] = useState<boolean>(false);
  const [openFaq, setOpenFaq] = useState<boolean>(false);
  const [rolledBackToVersion, setRolledBackToVersion] = useState<string | null>(null);

  const showTechDetails = showTechnicalMetadata ?? isAdmin;

  return (
    <section
      aria-label={labels.centerHeaderTitle}
      data-testid="contextual-help-hybrid-panel"
      data-mode="HELP_MENU_CENTER"
      data-active-section={activeSectionId ?? ""}
      className="w-full max-w-4xl rounded-xl border border-surface-border bg-surface-elevated p-4 text-xs text-text-primary space-y-3"
    >
      <HelpArticleHeaderBlock
        article={article}
        pack={pack}
        redisCacheKey={redisCacheKey}
        mergedLayers={mergedLayers}
        rollbackAvailable={rollbackAvailable}
        showTechDetails={showTechDetails}
        rolledBackToVersion={rolledBackToVersion}
        onSetRolledBack={setRolledBackToVersion}
        labels={labels}
        autonomousBadgeLabels={autonomousBadgeLabels}
        onRollbackVersion={onRollbackVersion}
        onInvalidateAndRestoreAutonomousHelp={onInvalidateAndRestoreAutonomousHelp}
      />

      <HelpCoreNarrativeBlocks article={article} labels={labels} showStepsBlock={false} />

      {article.stepByStepItems.length > 0 && (
        <HelpAccordionSection
          title={labels.stepByStepAccordionTitle}
          items={article.stepByStepItems}
          ordered
          open={openSteps}
          onToggle={() => setOpenSteps((prev) => !prev)}
          btnTestId="help-accordion-steps-btn"
          contentTestId="help-accordion-steps-content"
        />
      )}

      {article.keyTermsItems.length > 0 && (
        <HelpAccordionSection
          title={labels.keyTermsAccordionTitle}
          items={article.keyTermsItems}
          open={openTerms}
          onToggle={() => setOpenTerms((prev) => !prev)}
          btnTestId="help-accordion-terms-btn"
          contentTestId="help-accordion-terms-content"
        />
      )}

      {article.faqItems.length > 0 && (
        <HelpAccordionSection
          title={labels.faqAccordionTitle}
          items={article.faqItems}
          open={openFaq}
          onToggle={() => setOpenFaq((prev) => !prev)}
          btnTestId="help-accordion-faq-btn"
          contentTestId="help-accordion-faq-content"
        />
      )}

      <HelpFooterActions
        route={route}
        article={article}
        isAdmin={isAdmin}
        rollbackAvailable={rollbackAvailable}
        rolledBackToVersion={rolledBackToVersion}
        onSetRolledBack={setRolledBackToVersion}
        labels={labels}
        askAssistantPrefill={askAssistantPrefill}
        onRollbackVersion={onRollbackVersion}
        onAskAssistantOnScreen={onAskAssistantOnScreen}
        requireAssistantCallback
      />
    </section>
  );
}
