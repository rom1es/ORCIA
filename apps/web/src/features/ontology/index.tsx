import {
  OntologyAndKbExplorerPanel,
  OrciaAlertBanner,
  OrciaIcon,
  type UiOntologyLevel,
} from "@orcia/ui";
import React from "react";
import { useI18n } from "../../i18n";
import { OntologyPromotionProposalsTab } from "./OntologyPromotionProposalsTab";
import { useOntologyFeatureController } from "./useOntologyFeatureController";

export function OntologyFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const copy = dictionary.ontologyGlossary;
  const {
    activeTab, setActiveTab, concepts, writableScopes, proposals, pendingCount,
    tripartiteEdges, staleAlerts, conceptName, setConceptName, conceptDef, setConceptDef,
    selectedScopeIdx, setSelectedScopeIdx, isSaving, isAuditingTripartite, busyProposalId,
    feedbackBanner, errorBanner, handleAddConcept, handleAuditDocVsCode,
    handleProposePromotion, handleDecideProposal,
  } = useOntologyFeatureController(locale, copy);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <nav role="tablist" className="orcia-ds-tabs">
        <button
          type="button"
          role="tab"
          data-testid="ontology-tab-explorer"
          aria-selected={activeTab === "EXPLORER"}
          onClick={() => setActiveTab("EXPLORER")}
          className="orcia-ds-tab"
        >
          <OrciaIcon name="bookOpen" /> <span>{copy.tabExplorer}</span>
        </button>
        <button
          type="button"
          role="tab"
          data-testid="ontology-tab-proposals"
          aria-selected={activeTab === "PROPOSALS"}
          onClick={() => setActiveTab("PROPOSALS")}
          className="orcia-ds-tab"
        >
          <OrciaIcon name="promoteUp" />{" "}
          <span>
            {pendingCount > 0 ? `${copy.tabProposalsPrefix} (${pendingCount})` : copy.tabProposalsPrefix}
          </span>
        </button>
      </nav>

      {errorBanner && (
        <OrciaAlertBanner tone="crimson" role="alert" testId="ontology-error-banner">
          {errorBanner}
        </OrciaAlertBanner>
      )}
      {feedbackBanner && (
        <OrciaAlertBanner tone="emerald" testId="ontology-feedback-banner">
          {feedbackBanner}
        </OrciaAlertBanner>
      )}

      {activeTab === "EXPLORER" ? (
        <>
          <section
            data-testid="ontology-create-concept-card"
            className="orcia-bento-card"
            style={{ display: "flex", flexDirection: "column", gap: "10px" }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <strong>{copy.addSectionTitle}</strong>
            </div>

            {writableScopes.length === 0 ? (
              <p
                data-testid="ontology-readonly-notice"
                style={{ margin: 0, fontSize: "12px", color: "var(--color-muted-foreground)" }}
              >
                {copy.noWritableLevelBanner}
              </p>
            ) : (
              <form
                data-testid="ontology-create-concept-form"
                autoComplete="off"
                data-lpignore="true"
                data-form-type="other"
                onSubmit={handleAddConcept}
                style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}
              >
                <select
                  data-testid="ontology-level-select"
                  value={String(selectedScopeIdx)}
                  onChange={(e) => setSelectedScopeIdx(Number(e.target.value))}
                  style={{
                    padding: "7px 10px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-border)",
                    backgroundColor: "var(--color-surface-card)",
                    color: "var(--color-foreground)",
                  }}
                >
                  {writableScopes.map((opt, idx) => {
                    const levelLabel = copy.levelLabels[opt.level as UiOntologyLevel] ?? opt.level;
                    const displayLabel =
                      opt.label.trim().toLowerCase() === levelLabel.trim().toLowerCase()
                        ? levelLabel
                        : `${levelLabel} · ${opt.label}`;
                    return (
                      <option key={`${opt.level}:${opt.scope_id}`} value={String(idx)}>
                        {displayLabel}
                      </option>
                    );
                  })}
                </select>
                <input
                  type="text"
                  autoComplete="off"
                  data-lpignore="true"
                  data-1p-ignore="true"
                  data-bwignore="true"
                  data-form-type="other"
                  data-testid="ontology-concept-name-input"
                  value={conceptName}
                  onChange={(e) => setConceptName(e.target.value)}
                  placeholder={copy.termPlaceholder}
                  style={{
                    flex: 1,
                    minWidth: "180px",
                    padding: "7px 10px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-border)",
                  }}
                />
                <input
                  type="text"
                  autoComplete="off"
                  data-lpignore="true"
                  data-1p-ignore="true"
                  data-bwignore="true"
                  data-form-type="other"
                  data-testid="ontology-concept-def-input"
                  value={conceptDef}
                  onChange={(e) => setConceptDef(e.target.value)}
                  placeholder={copy.defPlaceholder}
                  style={{
                    flex: 2,
                    minWidth: "220px",
                    padding: "7px 10px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-border)",
                  }}
                />
                <button
                  type="submit"
                  disabled={isSaving || !conceptName.trim()}
                  data-testid="ontology-create-concept-btn"
                  className="orcia-ds-btn orcia-ds-btn-primary"
                >
                  {isSaving ? copy.addingLabel : copy.addButtonLabel}
                </button>
              </form>
            )}
          </section>

          <div className="orcia-bento-card">
            <OntologyAndKbExplorerPanel
              concepts={concepts}
              tripartiteEdges={tripartiteEdges}
              staleAlerts={staleAlerts}
              labels={dictionary.ontologyExplorer}
              auditing={isAuditingTripartite}
              onProposePromotion={(c) => void handleProposePromotion(c)}
              onAuditDocVsCode={handleAuditDocVsCode}
            />
          </div>
        </>
      ) : (
        <OntologyPromotionProposalsTab
          proposals={proposals}
          copy={copy}
          busyProposalId={busyProposalId}
          onDecideProposal={(id, decision, comment) =>
            void handleDecideProposal(id, decision, comment)
          }
        />
      )}
    </div>
  );
}
