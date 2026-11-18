import {
  ContextualInfoTriggerButton,
  OntologyAndKbExplorerPanel,
  OrciaAlertBanner,
  OrciaIcon,
  type UiOntologyConceptView,
  type UiOntologyLevel,
} from "@orcia/ui";
import React, { useCallback, useEffect, useState } from "react";
import {
  decideOntologyPromotionToApi,
  fetchOntologyConceptsFromApi,
  fetchOntologyPromotionsFromApi,
  proposeOntologyPromotionToApi,
  slugifyScopedConceptKey,
  upsertOntologyConceptToApi,
  type OntologyPromotionProposalDetailItem,
  type WritableScopeOptionItem,
} from "../../components/ontologyApiBridge";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
import { OntologyPromotionProposalsTab } from "./OntologyPromotionProposalsTab";

export function OntologyFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { openHelpSection } = useShellNavigation();
  const copy = dictionary.ontologyGlossary;
  const typedLocale = locale === "en" ? "en" : "fr";

  const [activeTab, setActiveTab] = useState<"EXPLORER" | "PROPOSALS">("EXPLORER");
  const [concepts, setConcepts] = useState<UiOntologyConceptView[]>([]);
  const [writableScopes, setWritableScopes] = useState<WritableScopeOptionItem[]>([]);
  const [proposals, setProposals] = useState<OntologyPromotionProposalDetailItem[]>([]);
  const [pendingCount, setPendingCount] = useState<number>(0);

  const [conceptName, setConceptName] = useState("");
  const [conceptDef, setConceptDef] = useState("");
  const [selectedScopeIdx, setSelectedScopeIdx] = useState<number>(0);
  const [isSaving, setIsSaving] = useState(false);
  const [busyProposalId, setBusyProposalId] = useState<string | null>(null);
  const [feedbackBanner, setFeedbackBanner] = useState<string | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const loadOntologyData = useCallback(async () => {
    try {
      const [conceptsRes, promosRes] = await Promise.all([
        fetchOntologyConceptsFromApi(typedLocale),
        fetchOntologyPromotionsFromApi(typedLocale),
      ]);
      setConcepts(conceptsRes.concepts);
      setWritableScopes(conceptsRes.writableScopes);
      setProposals(promosRes.proposals);
      setPendingCount(promosRes.pendingCount);
      setSelectedScopeIdx(0);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : copy.errorFallback;
      setErrorBanner(msg);
    }
  }, [typedLocale, copy.errorFallback]);

  useEffect(() => {
    void loadOntologyData();
  }, [loadOntologyData]);

  const activeScopeOption = writableScopes[selectedScopeIdx] ?? writableScopes[0] ?? null;

  const handleAddConcept = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!conceptName.trim() || !activeScopeOption) return;
    setIsSaving(true);
    setErrorBanner(null);
    setFeedbackBanner(null);
    try {
      const term = conceptName.trim();
      const def = conceptDef.trim() || term;
      const targetLevel = activeScopeOption.level as UiOntologyLevel;
      await upsertOntologyConceptToApi(typedLocale, {
        conceptKey: slugifyScopedConceptKey(term, targetLevel, activeScopeOption.scope_id),
        canonicalTerm: term,
        level: targetLevel,
        scopeId: activeScopeOption.scope_id,
        definitionText: def,
        profileTranslations: {
          EXECUTIVE: def,
          PM_BUSINESS: def,
          ARCHITECT: def,
          TECH_LEAD: def,
          DEVELOPER: def,
          SECOPS: def,
        },
      });
      setConceptName("");
      setConceptDef("");
      setFeedbackBanner(`${copy.createdSuccessPrefix} ${term}`);
      await loadOntologyData();
    } catch (err: unknown) {
      setErrorBanner(err instanceof Error ? err.message : copy.errorFallback);
    } finally {
      setIsSaving(false);
    }
  };

  const handleProposePromotion = async (concept: UiOntologyConceptView) => {
    setErrorBanner(null);
    setFeedbackBanner(null);
    try {
      await proposeOntologyPromotionToApi(typedLocale, {
        concept_key: concept.conceptKey,
        target_level: concept.nextPromotionLevel ?? undefined,
        target_scope_id: concept.nextPromotionScopeId ?? undefined,
      });
      setFeedbackBanner(`${copy.proposedSuccessPrefix} ${concept.canonicalTerm}`);
      await loadOntologyData();
    } catch (err: unknown) {
      setErrorBanner(err instanceof Error ? err.message : copy.errorFallback);
    }
  };

  const handleDecideProposal = async (
    proposalId: string,
    decision: "APPROVE" | "REJECT",
    comment?: string,
  ) => {
    setBusyProposalId(proposalId);
    setErrorBanner(null);
    setFeedbackBanner(null);
    try {
      await decideOntologyPromotionToApi(typedLocale, proposalId, {
        decision,
        review_comment: comment?.trim() || undefined,
      });
      setFeedbackBanner(
        decision === "APPROVE" ? copy.decisionSuccessApproved : copy.decisionSuccessRejected,
      );
      await loadOntologyData();
    } catch (err: unknown) {
      setErrorBanner(err instanceof Error ? err.message : copy.errorFallback);
    } finally {
      setBusyProposalId(null);
    }
  };

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
          <span>{`${copy.tabProposalsPrefix} (${pendingCount})`}</span>
        </button>
      </nav>

      {errorBanner && (
        <OrciaAlertBanner tone="crimson" testId="ontology-error-banner">
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
              <ContextualInfoTriggerButton
                sectionId="glossary-rules"
                label={copy.addHelpLabel}
                onOpenHelpSection={openHelpSection}
              />
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
                  {writableScopes.map((opt, idx) => (
                    <option key={`${opt.level}:${opt.scope_id}`} value={String(idx)}>
                      {`${copy.levelLabels[opt.level as UiOntologyLevel] ?? opt.level} · ${opt.label}`}
                    </option>
                  ))}
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
              tripartiteEdges={[]}
              staleAlerts={[]}
              labels={dictionary.ontologyExplorer}
              onProposePromotion={(c) => void handleProposePromotion(c)}
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
