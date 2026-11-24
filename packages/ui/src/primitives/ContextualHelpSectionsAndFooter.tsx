import React from "react";
import { renderInlineMarkdownNodes } from "../components/FormattedMarkdownContent";
import { OrciaIcon } from "../components/icons";
import type {
  ContextualHelpColumnAndCenterLabels,
  UiContextualHelpArticleView,
  UiContextualHelpSectionItem,
} from "./ContextualHelpTypes";

export function HelpAccordionSection({
  title,
  items,
  ordered,
  open,
  onToggle,
  btnTestId,
  contentTestId,
}: {
  readonly title: string;
  readonly items: readonly string[];
  readonly ordered?: boolean;
  readonly open: boolean;
  readonly onToggle: () => void;
  readonly btnTestId: string;
  readonly contentTestId: string;
}): React.ReactElement {
  return (
    <div className="rounded-lg border border-surface-border overflow-hidden">
      <button
        type="button"
        aria-expanded={open}
        data-testid={btnTestId}
        onClick={onToggle}
        className="w-full px-3 py-2 bg-surface-secondary text-left font-semibold flex items-center justify-between"
      >
        <span>{title}</span>
        <OrciaIcon name={open ? "caretDown" : "caretRight"} />
      </button>
      {open &&
        (ordered ? (
          <ol
            data-testid={contentTestId}
            className="list-decimal space-y-1.5 bg-surface-primary p-3 pl-5 text-text-secondary"
          >
            {items.map((item, idx) => (
              <li key={idx}>{renderInlineMarkdownNodes(item)}</li>
            ))}
          </ol>
        ) : (
          <ul
            data-testid={contentTestId}
            className="list-disc space-y-1.5 bg-surface-primary p-3 pl-5 text-text-secondary"
          >
            {items.map((item, idx) => (
              <li key={idx}>{renderInlineMarkdownNodes(item)}</li>
            ))}
          </ul>
        ))}
    </div>
  );
}

export function HelpTargetedSectionsList({
  sections,
  activeSectionId,
  targetedHelpBadgeLabel,
  sectionRefs,
}: {
  readonly sections: readonly UiContextualHelpSectionItem[];
  readonly activeSectionId: string | null;
  readonly targetedHelpBadgeLabel: string;
  readonly sectionRefs: React.MutableRefObject<Record<string, HTMLDivElement | null>>;
}): React.ReactElement | null {
  if (sections.length === 0) return null;
  return (
    <div data-testid="contextual-help-sections-list" className="space-y-2">
      {sections.map((sec) => {
        const isActive = activeSectionId === sec.sectionId;
        return (
          <div
            key={sec.sectionId}
            id={`help-section-${sec.sectionId}`}
            ref={(el) => {
              sectionRefs.current[sec.sectionId] = el;
            }}
            data-testid={`help-section-${sec.sectionId}`}
            data-active={isActive ? "true" : "false"}
            className={`orcia-help-section-card ${
              isActive ? "orcia-help-section-card--active" : ""
            } space-y-1`}
          >
            <div className="font-semibold text-text-primary flex items-center justify-between gap-1.5 flex-wrap">
              <span className="flex items-center gap-1.5">
                <OrciaIcon name="infoSymbol" />
                <span>{sec.title}</span>
              </span>
              {isActive && (
                <span
                  data-testid="contextual-help-pinned-active-badge"
                  className="rounded px-1.5 py-0.5 text-[10px] font-semibold"
                  style={{
                    backgroundColor: "var(--color-action-primary-subtle)",
                    color: "var(--color-action-primary)",
                  }}
                >
                  {targetedHelpBadgeLabel}
                </span>
              )}
            </div>
            <p className="text-text-secondary leading-relaxed">
              {renderInlineMarkdownNodes(sec.body)}
            </p>
          </div>
        );
      })}
    </div>
  );
}

export function HelpFooterActions({
  route,
  article,
  isAdmin,
  rollbackAvailable,
  rolledBackToVersion,
  onSetRolledBack,
  labels,
  askAssistantPrefill,
  onRollbackVersion,
  onAskAssistantOnScreen,
  requireAssistantCallback,
}: {
  readonly route: string;
  readonly article: UiContextualHelpArticleView;
  readonly isAdmin: boolean;
  readonly rollbackAvailable: boolean;
  readonly rolledBackToVersion: string | null;
  readonly onSetRolledBack: (v: string) => void;
  readonly labels: ContextualHelpColumnAndCenterLabels;
  readonly askAssistantPrefill?: string;
  readonly onRollbackVersion?: (resourceId: string) => void;
  readonly onAskAssistantOnScreen?: (route: string, prefillPrompt: string) => void;
  readonly requireAssistantCallback?: boolean;
}): React.ReactElement {
  const prefillPrompt =
    askAssistantPrefill ??
    (labels.askAssistantPrefillTemplate
      ? labels.askAssistantPrefillTemplate
          .replace("{route}", route)
          .replace("{title}", article.title)
      : `${route} (${article.title})`);

  return (
    <>
      {isAdmin && rollbackAvailable && (
        <div className="pt-1 flex items-center justify-between gap-2">
          <button
            type="button"
            data-testid="contextual-help-rollback-btn"
            onClick={() => {
              onSetRolledBack(article.previousVersion ?? "1.0.0");
              onRollbackVersion?.(article.resourceId);
            }}
            className="px-2.5 py-1 rounded border border-surface-border bg-surface-secondary font-medium text-text-primary"
          >
            {labels.rollbackButtonLabel}
            {article.previousVersion ? ` (v${article.previousVersion})` : ""}
          </button>
          {rolledBackToVersion !== null && (
            <span
              data-testid="contextual-help-rollback-banner"
              className="font-mono text-[11px] text-status-success"
            >
              {labels.rollbackCompletedPrefix} v{rolledBackToVersion}
            </span>
          )}
        </div>
      )}

      {(!requireAssistantCallback || onAskAssistantOnScreen) && (
        <div className="pt-2 border-t border-surface-border">
          <button
            type="button"
            data-testid="contextual-help-ask-assistant-btn"
            onClick={() => onAskAssistantOnScreen?.(route, prefillPrompt)}
            className="w-full py-1.5 px-3 rounded-lg bg-brand-primary text-[var(--color-primary-foreground)] font-medium text-center"
          >
            {labels.askAssistantOnScreenCta}
          </button>
        </div>
      )}
    </>
  );
}
