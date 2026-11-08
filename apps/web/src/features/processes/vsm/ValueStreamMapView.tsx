import React, { useEffect, useMemo, useState } from "react";
import { useShellNavigation } from "../../../components/ShellContainer";
import { useI18n } from "../../../i18n";
import { INITIAL_VSM_SPEC } from "../processStudioV2Data";
import { ReturnLoopsSvgOverlay, type VsmReturnLoopItem } from "./ReturnLoopsSvgOverlay";
import { StepDetailSheet } from "./StepDetailSheet";

export type VsmComparisonMode = "today" | "tomorrow" | "compare";

export function ValueStreamMapView({ vsmId }: { vsmId?: string }) {
  const { locale } = useI18n();
  const { navigateToRoute } = useShellNavigation();
  const isFr = locale === "fr";

  const vsm = INITIAL_VSM_SPEC;
  const allSteps = useMemo(
    () => vsm.phases.flatMap((phase) => phase.steps.map((step) => ({ ...step, phase }))),
    [vsm],
  );
  const allLoops = (vsm.return_loops ?? []) as unknown as VsmReturnLoopItem[];

  const [mode, setMode] = useState<VsmComparisonMode>("compare");
  const [selectedStepNum, setSelectedStepNum] = useState<string | null>("01");
  const [highlightedStepNum, setHighlightedStepNum] = useState<string | null>(null);
  const [showOpportunitiesDrawer, setShowOpportunitiesDrawer] = useState<boolean>(false);
  const [presentationMode, setPresentationMode] = useState<boolean>(false);

  const selectedStep = useMemo(
    () => allSteps.find((s) => s.num === selectedStepNum) ?? null,
    [allSteps, selectedStepNum],
  );

  // Keyboard navigation in Presentation Mode (← / → / Escape)
  useEffect(() => {
    const onKeyDown = (ev: KeyboardEvent) => {
      if (!presentationMode && !selectedStepNum) return;
      if (ev.key === "Escape") {
        setPresentationMode(false);
        return;
      }
      if (ev.key === "ArrowRight" || ev.key === "ArrowLeft") {
        const currentIndex = allSteps.findIndex((s) => s.num === (selectedStepNum ?? "01"));
        if (currentIndex < 0) return;
        const delta = ev.key === "ArrowRight" ? 1 : -1;
        const nextIndex = (currentIndex + delta + allSteps.length) % allSteps.length;
        const nextStep = allSteps[nextIndex];
        if (nextStep) {
          setSelectedStepNum(nextStep.num);
          setHighlightedStepNum(nextStep.num);
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [allSteps, presentationMode, selectedStepNum]);

  return (
    <section
      data-testid="vsm-interactive-view"
      data-vsm-id={vsmId ?? vsm.id}
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      {/* Top Bar: Title, 3-Mode Comparison Switcher, Opportunities Drawer Toggle & Presentation Mode */}
      <header
        className="orcia-bento-card"
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
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
                onClick={() => navigateToRoute("/processes")}
                className="orcia-ds-btn-secondary"
              >
                {isFr ? "← Retour au Hub Processus" : "← Back to Processes Hub"}
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
            {/* 3-Mode Comparison Switcher */}
            <div
              role="tablist"
              aria-label="Mode de comparaison VSM"
              data-testid="vsm-comparison-mode-switcher"
              className="orcia-ds-tabs"
            >
              {(
                [
                  { key: "today", label: isFr ? "Aujourd'hui" : "Today" },
                  { key: "tomorrow", label: isFr ? "Avec les agents" : "With Agents" },
                  { key: "compare", label: isFr ? "Comparer" : "Compare" },
                ] as const
              ).map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  role="tab"
                  aria-selected={mode === tab.key}
                  data-testid={`vsm-mode-${tab.key}`}
                  onClick={() => setMode(tab.key)}
                  className="orcia-ds-tab"
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <button
              type="button"
              data-testid="vsm-toggle-opportunities-drawer-btn"
              onClick={() => setShowOpportunitiesDrawer((prev) => !prev)}
              className="orcia-ds-btn-secondary"
            >
              {isFr
                ? `💡 Opportunités (${vsm.opportunities.length})`
                : `💡 Opportunities (${vsm.opportunities.length})`}
            </button>

            <button
              type="button"
              data-testid="vsm-toggle-presentation-mode-btn"
              onClick={() => setPresentationMode((prev) => !prev)}
              className="orcia-ds-btn-primary"
            >
              {presentationMode
                ? isFr
                  ? "⏹ Quitter Présentation"
                  : "⏹ Exit Presentation"
                : isFr
                  ? "▶ Présenter (Clavier ←/→)"
                  : "▶ Present (←/→ Keys)"}
            </button>
          </div>
        </div>

        {/* Socle de Connaissance Confluence Transverse Banner (CA-9.2.4) */}
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
                Alimente Étape {stepNum}
              </span>
            ))}
          </div>
        </div>
      </header>

      {/* Opportunities Drawer (P1, P2, P3) */}
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
            <h3 style={{ margin: 0, fontSize: "15px" }}>
              {isFr
                ? "Tiroir des Opportunités d'Enrichissement Agentique (Priorités P1, P2, P3)"
                : "Agentic Enrichment Opportunities Drawer (Priorities P1, P2, P3)"}
            </h3>
            <button
              type="button"
              data-testid="vsm-close-opportunities-drawer-btn"
              onClick={() => setShowOpportunitiesDrawer(false)}
              className="orcia-ds-btn-secondary"
            >
              {isFr ? "Fermer" : "Close"}
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

      {/* Dynamic Collision-Free Return Loops SVG Overlay */}
      <ReturnLoopsSvgOverlay
        loops={allLoops}
        highlightedStepNum={highlightedStepNum ?? selectedStepNum}
        onSelectLoopStep={(fromNum, toNum) => {
          setSelectedStepNum(fromNum);
          setHighlightedStepNum(toNum);
        }}
        isFr={isFr}
      />

      {/* 4 Phases & 11 Steps Interactive Grid */}
      {vsm.phases.map((phase) => (
        <div
          key={phase.num}
          data-testid={`vsm-phase-section-${phase.num}`}
          className="orcia-bento-card"
          style={{ display: "flex", flexDirection: "column", gap: "12px" }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "8px",
              borderBottom: "1px solid var(--color-border-subtle)",
              paddingBottom: "8px",
            }}
          >
            <div>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "11.5px",
                  fontWeight: 700,
                  color: "var(--color-primary-cobalt)",
                }}
              >
                PHASE {phase.num} · ÉTAPES {phase.steps_range}
              </span>
              <h2 style={{ margin: "2px 0 0 0", fontSize: "17px" }}>
                {phase.name} — {phase.goal}
              </h2>
            </div>
            <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
              {phase.deliverables_summary}
            </span>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
              gap: "12px",
            }}
          >
            {phase.steps.map((step) => {
              const isSelected = selectedStepNum === step.num;
              return (
                <article
                  key={step.num}
                  data-testid={`vsm-step-card-${step.num}`}
                  onMouseEnter={() => setHighlightedStepNum(step.num)}
                  onMouseLeave={() => setHighlightedStepNum(null)}
                  className="rounded border p-3.5"
                  style={{
                    backgroundColor: isSelected
                      ? "var(--color-action-primary-subtle)"
                      : "var(--color-bg-elevated)",
                    borderColor: isSelected
                      ? "var(--color-primary-cobalt)"
                      : "var(--color-border-subtle)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                    justifyContent: "space-between",
                  }}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        gap: "6px",
                        flexWrap: "wrap",
                      }}
                    >
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontWeight: 700,
                          fontSize: "12px",
                          color: "var(--color-primary-cobalt)",
                        }}
                      >
                        ÉTAPE {step.num}
                      </span>
                      <span
                        className="rounded px-2 py-0.5 text-xs font-semibold"
                        style={{
                          backgroundColor: "var(--color-gate-emerald-bg)",
                          color: "var(--color-gate-emerald)",
                        }}
                      >
                        {step.actor_label} · {step.status_badge}
                      </span>
                    </div>

                    <h3 style={{ margin: 0, fontSize: "15px" }}>{step.title}</h3>
                    <p style={{ margin: 0, fontSize: "12px", color: "var(--color-text-secondary)" }}>
                      {step.summary}
                    </p>

                    {/* Comparison Display according to active mode */}
                    {(mode === "today" || mode === "compare") ? (
                      <div
                        data-testid={`vsm-step-${step.num}-today-box`}
                        className="rounded border p-2 text-xs"
                        style={{
                          backgroundColor: "var(--color-surface-card)",
                          borderColor: "var(--color-border-subtle)",
                        }}
                      >
                        <strong style={{ color: "var(--color-arbitration-amber)" }}>
                          {isFr ? "Aujourd'hui :" : "Today:"}
                        </strong>{" "}
                        {step.today.activities}
                      </div>
                    ) : null}

                    {(mode === "tomorrow" || mode === "compare") ? (
                      <div
                        data-testid={`vsm-step-${step.num}-tomorrow-box`}
                        className="rounded border p-2 text-xs"
                        style={{
                          backgroundColor: "var(--color-gate-emerald-bg)",
                          borderColor: "var(--color-gate-emerald)",
                        }}
                      >
                        <strong style={{ color: "var(--color-gate-emerald)" }}>
                          {isFr ? "Avec les agents :" : "With agents:"}
                        </strong>{" "}
                        {step.tomorrow.activities}
                        <div style={{ marginTop: "3px", fontWeight: 600 }}>
                          ⚡ {step.tomorrow.gains}
                        </div>
                      </div>
                    ) : null}

                    {/* Human Passage Point Diamond (◆) */}
                    {step.passage_point ? (
                      <div
                        data-testid={`vsm-passage-diamond-${step.num}`}
                        onMouseEnter={() => setHighlightedStepNum(step.num)}
                        className="rounded border px-2.5 py-1.5 text-xs"
                        style={{
                          backgroundColor: "var(--color-arbitration-bg)",
                          borderColor: "var(--color-arbitration-amber)",
                          color: "var(--color-text-primary)",
                        }}
                      >
                        <strong style={{ color: "var(--color-arbitration-amber)" }}>
                          ◆ {step.passage_point.decision}
                        </strong>
                        <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
                          {step.passage_point.question}
                        </div>
                      </div>
                    ) : null}
                  </div>

                  {/* Step Action Bridges */}
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                    <button
                      type="button"
                      data-testid={`open-step-sheet-btn-${step.num}`}
                      onClick={() => setSelectedStepNum(step.num)}
                      className="orcia-ds-btn-secondary"
                    >
                      {isFr ? "📄 Fiche 6 Onglets" : "📄 6-Tab Sheet"}
                    </button>
                    {step.linked_workflow_id ? (
                      <>
                        <button
                          type="button"
                          data-testid={`vsm-step-studio-btn-${step.num}`}
                          onClick={() => navigateToRoute(`/processes/studio/${step.linked_workflow_id}`)}
                          className="orcia-ds-btn-secondary"
                        >
                          {isFr ? "✏️ Studio WF" : "✏️ WF Studio"}
                        </button>
                        <button
                          type="button"
                          data-testid={`vsm-step-run-btn-${step.num}`}
                          onClick={() => navigateToRoute(`/processes/studio/${step.linked_workflow_id}`)}
                          className="orcia-ds-btn-primary"
                        >
                          {isFr ? "▷ Exécuter" : "▷ Execute"}
                        </button>
                      </>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      ))}

      {/* Active 6-Tab Step Detail Sheet */}
      {selectedStep ? (
        <StepDetailSheet
          step={selectedStep}
          allLoops={allLoops}
          onClose={() => setSelectedStepNum(null)}
          onOpenStudio={(wfId) => navigateToRoute(`/processes/studio/${wfId}`)}
          onExecuteWorkflow={(wfId) => navigateToRoute(`/processes/studio/${wfId}`)}
          isFr={isFr}
        />
      ) : null}
    </section>
  );
}
