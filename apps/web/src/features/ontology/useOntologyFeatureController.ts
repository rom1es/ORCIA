import type {
  UiOntologyConceptView,
  UiOntologyLevel,
  UiStaleAlertView,
  UiTripartiteEdgeView,
} from "@orcia/ui";
import { useCallback, useEffect, useState } from "react";
import {
  auditDocVsCodeToApi,
  decideOntologyPromotionToApi,
  fetchOntologyConceptsFromApi,
  fetchOntologyPromotionsFromApi,
  fetchOntologyRagStateFromApi,
  proposeOntologyPromotionToApi,
  slugifyScopedConceptKey,
  upsertOntologyConceptToApi,
  type OntologyPromotionProposalDetailItem,
  type WritableScopeOptionItem,
} from "../../components/ontologyApiBridge";
import type { OntologyGlossaryCopy } from "../../i18n/locales/ontology_glossary_labels";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";

export function useOntologyFeatureController(
  typedLocale: "fr" | "en",
  copy: OntologyGlossaryCopy,
) {
  const [activeTab, setActiveTab] = useState<"EXPLORER" | "PROPOSALS">("EXPLORER");
  const [concepts, setConcepts] = useState<UiOntologyConceptView[]>([]);
  const [writableScopes, setWritableScopes] = useState<WritableScopeOptionItem[]>([]);
  const [proposals, setProposals] = useState<OntologyPromotionProposalDetailItem[]>([]);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [tripartiteEdges, setTripartiteEdges] = useState<UiTripartiteEdgeView[]>([]);
  const [staleAlerts, setStaleAlerts] = useState<UiStaleAlertView[]>([]);
  const [conceptName, setConceptName] = useState("");
  const [conceptDef, setConceptDef] = useState("");
  const [selectedScopeIdx, setSelectedScopeIdx] = useState<number>(0);
  const [isSaving, setIsSaving] = useState(false);
  const [isAuditingTripartite, setIsAuditingTripartite] = useState(false);
  const [busyProposalId, setBusyProposalId] = useState<string | null>(null);
  const [feedbackBanner, setFeedbackBanner] = useState<string | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const loadOntologyData = useCallback(async () => {
    try {
      const [conceptsRes, promosRes, ragStateRes] = await Promise.all([
        fetchOntologyConceptsFromApi(typedLocale),
        fetchOntologyPromotionsFromApi(typedLocale),
        fetchOntologyRagStateFromApi(typedLocale),
      ]);
      setConcepts(conceptsRes.concepts);
      setWritableScopes(conceptsRes.writableScopes);
      setProposals(promosRes.proposals);
      setPendingCount(promosRes.pendingCount);
      setTripartiteEdges(ragStateRes.tripartiteEdges);
      setStaleAlerts(ragStateRes.staleAlerts);
      setSelectedScopeIdx(0);
    } catch (err: unknown) {
      setErrorBanner(
        formatRfc9457ErrorToBanner(err, typedLocale, typedLocale === "fr" ? "Glossaire métier" : "Business glossary").fullText,
      );
    }
  }, [typedLocale]);

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
        profileTranslations: { EXECUTIVE: def, PM_BUSINESS: def, ARCHITECT: def, TECH_LEAD: def, DEVELOPER: def, SECOPS: def },
      });
      setConceptName("");
      setConceptDef("");
      setFeedbackBanner(`${copy.createdSuccessPrefix} ${term}`);
      await loadOntologyData();
    } catch (err: unknown) {
      setErrorBanner(
        formatRfc9457ErrorToBanner(err, typedLocale, typedLocale === "fr" ? "Terme du glossaire" : "Glossary term").fullText,
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleAuditDocVsCode = async (draft: { confluenceUri: string; gitRepoUri: string; gitSymbol: string; jiraKey: string }) => {
    setIsAuditingTripartite(true);
    setErrorBanner(null);
    setFeedbackBanner(null);
    try {
      const wsScope =
        activeScopeOption && (activeScopeOption.level === "3_WORKSPACE" || activeScopeOption.level === "4_WORKSPACE")
          ? activeScopeOption
          : writableScopes.find((s) => s.level === "3_WORKSPACE" || s.level === "4_WORKSPACE");
      const res = await auditDocVsCodeToApi(typedLocale, {
        workspace_id: wsScope?.scope_id ?? null,
        confluence_uri: draft.confluenceUri,
        git_repo_uri: draft.gitRepoUri,
        git_symbol: draft.gitSymbol || "main",
        doc_rule_summary: draft.confluenceUri,
        code_rule_summary: draft.gitRepoUri,
        newer_done_jira_key: draft.jiraKey || null,
      });
      setFeedbackBanner(res.explanation);
      await loadOntologyData();
    } catch (err: unknown) {
      setErrorBanner(
        formatRfc9457ErrorToBanner(err, typedLocale, typedLocale === "fr" ? "Graphe tripartite" : "Tripartite graph").fullText,
      );
    } finally {
      setIsAuditingTripartite(false);
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
      setErrorBanner(
        formatRfc9457ErrorToBanner(err, typedLocale, typedLocale === "fr" ? "Proposition de promotion" : "Promotion proposal").fullText,
      );
    }
  };

  const handleDecideProposal = async (proposalId: string, decision: "APPROVE" | "REJECT", comment?: string) => {
    setBusyProposalId(proposalId);
    setErrorBanner(null);
    setFeedbackBanner(null);
    try {
      await decideOntologyPromotionToApi(typedLocale, proposalId, { decision, review_comment: comment?.trim() || undefined });
      setFeedbackBanner(decision === "APPROVE" ? copy.decisionSuccessApproved : copy.decisionSuccessRejected);
      await loadOntologyData();
    } catch (err: unknown) {
      setErrorBanner(
        formatRfc9457ErrorToBanner(err, typedLocale, typedLocale === "fr" ? "Terme du glossaire" : "Glossary term").fullText,
      );
    } finally {
      setBusyProposalId(null);
    }
  };

  return {
    activeTab, setActiveTab, concepts, writableScopes, proposals, pendingCount,
    tripartiteEdges, staleAlerts, conceptName, setConceptName, conceptDef, setConceptDef,
    selectedScopeIdx, setSelectedScopeIdx, isSaving, isAuditingTripartite, busyProposalId,
    feedbackBanner, errorBanner, handleAddConcept, handleAuditDocVsCode,
    handleProposePromotion, handleDecideProposal,
  };
}
