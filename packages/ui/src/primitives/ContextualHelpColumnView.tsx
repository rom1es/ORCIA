import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  HelpArticleHeaderBlock,
  HelpCoreNarrativeBlocks,
} from "./ContextualHelpSharedBlocks";
import {
  HelpAccordionSection,
  HelpFooterActions,
  HelpTargetedSectionsList,
} from "./ContextualHelpSectionsAndFooter";
import type {
  ContextualHelpColumnAndCenterProps,
  UiContextualHelpSectionItem,
} from "./ContextualHelpTypes";

/**
 * Zone 4 (`COLUMN_340PX`) — Renders the route-faithful contextual help panel with the 4 DESIGN.md blocks:
 * 1) À quoi sert cet écran, 2) EN N GESTES, 3) Amber box UN EXEMPLE RÉEL, 4) CE QUI COINCE SOUVENT.
 */
export function ContextualHelpColumnView({
  route,
  pack,
  redisCacheKey,
  mergedLayers,
  article,
  targetedSections,
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
  const [openTerms, setOpenTerms] = useState<boolean>(true);
  const [openFaq, setOpenFaq] = useState<boolean>(false);
  const [rolledBackToVersion, setRolledBackToVersion] = useState<string | null>(null);
  const panelRef = useRef<HTMLElement | null>(null);
  const sectionRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const effectiveSections: readonly UiContextualHelpSectionItem[] =
    targetedSections ?? article.sections ?? [];

  const orderedSections = useMemo(() => {
    if (!activeSectionId) return effectiveSections;
    const activeItem = effectiveSections.find((sec) => sec.sectionId === activeSectionId);
    if (!activeItem) return effectiveSections;
    return [activeItem, ...effectiveSections.filter((sec) => sec.sectionId !== activeSectionId)];
  }, [effectiveSections, activeSectionId]);

  useEffect(() => {
    setRolledBackToVersion(null);
  }, [article.resourceId, article.version]);

  useEffect(() => {
    if (!activeSectionId) return;
    const matchingSection = effectiveSections.find((sec) => sec.sectionId === activeSectionId);
    if (matchingSection?.category === "terms") setOpenTerms(true);
    else if (matchingSection?.category === "faq") setOpenFaq(true);

    const activeSectionEl = sectionRefs.current[activeSectionId];
    if (activeSectionEl && typeof activeSectionEl.scrollIntoView === "function") {
      activeSectionEl.scrollIntoView({ block: "nearest", behavior: "smooth" });
      return;
    }
    const helpAside = panelRef.current?.closest(
      '[data-testid="four-zone-contextual-help-column"]',
    ) as HTMLElement | null;
    const scroller = helpAside ?? panelRef.current;
    if (scroller) {
      scroller.scrollTop = 0;
      if (typeof scroller.scrollTo === "function") {
        scroller.scrollTo({ top: 0, behavior: "smooth" });
      }
    }
  }, [activeSectionId, effectiveSections]);

  const showTechDetails = showTechnicalMetadata ?? isAdmin;

  return (
    <section
      ref={panelRef}
      aria-label={labels.columnHeaderTitle}
      data-testid="contextual-help-hybrid-panel"
      data-mode="COLUMN_340PX"
      data-active-section={activeSectionId ?? ""}
      className="w-full rounded-xl border border-surface-border bg-surface-elevated p-3.5 text-xs text-text-primary space-y-3"
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
        titleAsHeading
      />

      <HelpTargetedSectionsList
        sections={orderedSections}
        activeSectionId={activeSectionId}
        targetedHelpBadgeLabel={labels.targetedHelpBadgeLabel}
        sectionRefs={sectionRefs}
      />

      <HelpCoreNarrativeBlocks article={article} labels={labels} showStepsBlock />

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
      />
    </section>
  );
}
