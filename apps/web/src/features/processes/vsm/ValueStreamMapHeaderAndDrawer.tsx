import React from "react";
import { formatI18nTemplate } from "../../../i18n";
import type { ProcessVsmExecutionUiDictionary } from "../../../i18n/locales/process_vsm_execution_ui_labels";
import type { UiVsmSpec } from "./mapApiVsmToUiSpec";

export type VsmComparisonMode = "today" | "tomorrow" | "compare";

export function ValueStreamMapHeaderAndDrawer({
  vsm,
  mode,
  presentationMode,
  showOpportunitiesDrawer,
  copy,
  onNavigateHub,
  onChangeMode,
  onToggleOpportunities,
  onTogglePresentation,
}: {
  readonly vsm: UiVsmSpec;
  readonly mode: VsmComparisonMode;
  readonly presentationMode: boolean;
  readonly showOpportunitiesDrawer: boolean;
  readonly copy: ProcessVsmExecutionUiDictionary["vsm"];
  readonly onNavigateHub: () => void;
  readonly onChangeMode: (nextMode: VsmComparisonMode) => void;
  readonly onToggleOpportunities: () => void;
  readonly onTogglePresentation: () => void;
}): React.JSX.Element {
  return (
    <>
      <header
        className="orcia-bento-card"
        style={{ display: "flex", flexDirection: "column", gap: "12px" }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
              <button
                type="button"
                data-testid="vsm-back-to-hub-btn"
                onClick={onNavigateHub}
                className="orcia-ds-btn-secondary"
              >
                {copy.backToHubBtn}
              </button>
              <span
                className="rounded px-2 py-0.5 text-xs font-semibold"
                style={{
                  backgroundColor: "var(--color-action-primary-subtle)",
                  color: "var(--color-primary-cobalt)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                {vsm.id} · v{vsm.version}
              </span>
            </div>
            <h1 style={{ margin: "6px 0 0 0", fontSize: "var(--font-size-h2)" }}>
              {vsm.title} — {vsm.subtitle}
            </h1>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <div
              role="tablist"
              aria-label={copy.modeSwitcherAriaLabel}
              data-testid="vsm-comparison-mode-switcher"
              className="orcia-ds-tabs"
            >
              {(
                [
                  { key: "today", label: copy.modeToday },
                  { key: "tomorrow", label: copy.modeTomorrow },
                  { key: "compare", label: copy.modeCompare },
                ] as const
              ).map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  role="tab"
                  aria-selected={mode === tab.key}
                  data-testid={`vsm-mode-${tab.key}`}
                  onClick={() => onChangeMode(tab.key)}
                  className="orcia-ds-tab"
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <button
              type="button"
              data-testid="vsm-toggle-opportunities-drawer-btn"
              onClick={onToggleOpportunities}
              className="orcia-ds-btn-secondary"
            >
              {formatI18nTemplate(copy.opportunitiesBtnTemplate, {
                count: vsm.opportunities.length,
              })}
            </button>

            <button
              type="button"
              data-testid="vsm-toggle-presentation-mode-btn"
              onClick={onTogglePresentation}
              className="orcia-ds-btn-primary"
            >
              {presentationMode ? copy.exitPresentationBtn : copy.enterPresentationBtn}
            </button>
          </div>
        </div>

        <div
          data-testid="vsm-knowledge-base-banner"
          className="rounded border p-3"
          style={{
            backgroundColor: "var(--color-ontology-bg)",
            borderColor: "var(--color-ontology-cyan)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "8px",
          }}
        >
          <div>
            <strong style={{ fontSize: "13px", color: "var(--color-ontology-cyan)" }}>
              📚 {vsm.knowledge_base.title}
            </strong>
            <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
              {vsm.knowledge_base.description}
            </div>
          </div>
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {vsm.knowledge_base.feeds_steps.map((stepNum) => (
              <span
                key={stepNum}
                className="rounded px-2 py-0.5 text-xs font-semibold"
                style={{
                  backgroundColor: "var(--color-surface-card)",
                  color: "var(--color-ontology-cyan)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                {formatI18nTemplate(copy.feedsStepTemplate, { step: stepNum })}
              </span>
            ))}
          </div>
        </div>
      </header>

      {showOpportunitiesDrawer ? (
        <div
          data-testid="vsm-opportunities-drawer"
          className="orcia-bento-card"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "10px",
            borderLeft: "4px solid var(--color-arbitration-amber)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ margin: 0, fontSize: "15px" }}>{copy.opportunitiesDrawerTitle}</h3>
            <button
              type="button"
              data-testid="vsm-close-opportunities-drawer-btn"
              onClick={onToggleOpportunities}
              className="orcia-ds-btn-secondary"
            >
              {copy.closeBtn}
            </button>
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "10px",
            }}
          >
            {vsm.opportunities.map((opp, idx) => (
              <div
                key={`${opp.priority}-${idx}`}
                data-testid={`vsm-opportunity-card-${idx}`}
                className="rounded border p-2.5 text-xs"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span
                    className="rounded px-1.5 py-0.5 font-bold"
                    style={{
                      backgroundColor: "var(--color-arbitration-bg)",
                      color: "var(--color-arbitration-amber)",
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    {opp.priority} · {opp.target_steps}
                  </span>
                </div>
                <div style={{ fontWeight: 700, marginTop: "4px", fontSize: "13px" }}>
                  {opp.title}
                </div>
                <div style={{ color: "var(--color-text-secondary)", marginTop: "3px" }}>
                  {opp.description}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </>
  );
}
