import {
  createOrciaApiClient,
  type ExceptionWaiverResponseItem,
  type GeneratedStarlarkMechanismResponse,
} from "@orcia/api-client";
import {
  DnaStarlarkCompilerAndGlossaryLifecycleView,
  type ControlCenterDatasourceItem,
  type ControlCenterWorkspaceGovItem,
  type ExceptionWaiverItem,
  type UiCompiledStarlarkMechanism,
  type UiGlossaryCandidateItem,
  type UiOntologyConceptView,
  type WorkspaceSubTabKey,
  WorkspaceFiveTabsAndExternalRebaseView,
} from "@orcia/ui";
import React, { useCallback, useEffect, useState } from "react";
import type { TranslationDictionary } from "../../i18n/types";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";

export interface WorkspaceDnaAndWaiversSectionProps {
  readonly isFr: boolean;
  readonly targetWorkspace: ControlCenterWorkspaceGovItem | null;
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly dictionary: TranslationDictionary;
  readonly onAddOntologyConcept: (concept: UiOntologyConceptView) => void;
  readonly onFeedback: (message: string | null) => void;
}

function mapWaiverItem(w: ExceptionWaiverResponseItem): ExceptionWaiverItem {
  return {
    waiverId: String(w.waiver_id),
    sourceUri: w.source_uri,
    conflictRuleId: w.conflict_rule_id,
    normLevel: w.norm_level,
    hasInviolableEnterpriseDirective:
      w.norm_level === "1_ENTERPRISE" ||
      w.dna_chain.some((n) => n.level === "1_ENTERPRISE" && n.inviolable),
    status: w.status,
    reason: w.reason,
  };
}

function mapMechanismItem(res: GeneratedStarlarkMechanismResponse): UiCompiledStarlarkMechanism {
  return {
    mechanismId: String(res.mechanism_id),
    ruleId: res.rule_id,
    scriptName: res.script_name,
    starlarkCode: res.starlark_code,
    sha256: res.sha256,
    explanationFr: res.explanation_fr,
    verifiedBadgeFr: res.verified_badge_fr,
    causalBreadcrumb: res.causal_breadcrumb,
    selfCorrected: Boolean(res.self_corrected),
    signedAndActive: Boolean(res.signed_and_active),
  };
}

function formatWorkspaceVisibilityLabel(mode: string | undefined, isFr: boolean): string {
  switch (mode) {
    case "PRIVATE_USER":
      return isFr ? "Privé personnel" : "Private personal";
    case "CONFIDENTIAL_RESTRICTED":
      return isFr ? "Confidentiel isolé" : "Confidential isolated";
    default:
      return isFr ? "Collectif d'équipe" : "Team shared";
  }
}

function formatWorkspacePhaseLabel(phase: string | undefined, isFr: boolean): string {
  switch (phase) {
    case "RUN":
      return isFr ? "Exploitation" : "Operations";
    case "MIGRATION":
      return isFr ? "Évolution" : "Evolution";
    default:
      return isFr ? "Construction" : "Build";
  }
}

function formatWorkspaceAccessModeLabel(accessMode: string | undefined, isFr: boolean): string {
  if (accessMode === "READ_ONLY_OBSERVER") {
    return isFr ? "Consultation seule" : "Read-only observer";
  }
  return isFr ? "Contributeur" : "Contributor";
}

export function WorkspaceDnaAndWaiversSection({
  isFr,
  targetWorkspace,
  datasources,
  ontologyConcepts,
  dictionary,
  onAddOntologyConcept,
  onFeedback,
}: WorkspaceDnaAndWaiversSectionProps): React.ReactElement | null {
  const [activeSubTab, setActiveSubTab] = useState<WorkspaceSubTabKey>("OVERVIEW");
  const [activeWaivers, setActiveWaivers] = useState<ExceptionWaiverItem[]>([]);
  const [compiledMechanism, setCompiledMechanism] =
    useState<UiCompiledStarlarkMechanism | null>(null);
  const [glossaryCandidates, setGlossaryCandidates] = useState<UiGlossaryCandidateItem[]>(
    [],
  );
  const [submitting, setSubmitting] = useState<boolean>(false);

  const targetWsId = targetWorkspace?.workspaceId ?? "";
  const targetWsSlug = targetWorkspace?.slug ?? targetWorkspace?.workspaceId ?? "";
  const locale = isFr ? "fr" : "en";

  const reloadWaiversAndMechanisms = useCallback(async () => {
    if (!targetWsId) {
      setActiveWaivers([]);
      setCompiledMechanism(null);
      return;
    }
    const client = createOrciaApiClient({ baseUrl: "", locale });
    const [waiversRows, mechanismRows] = await Promise.all([
      client.listWorkspaceExceptionWaivers(targetWsId, true),
      client.listDnaMechanisms(targetWsId),
    ]);
    setActiveWaivers(waiversRows.map(mapWaiverItem));
    setCompiledMechanism(mechanismRows[0] ? mapMechanismItem(mechanismRows[0]) : null);
  }, [targetWsId, locale]);

  useEffect(() => {
    if (!targetWsId) {
      setActiveWaivers([]);
      setCompiledMechanism(null);
      return;
    }
    let cancelled = false;
    void reloadWaiversAndMechanisms().catch((err: unknown) => {
      if (cancelled) return;
      onFeedback(
        `⚠️ ${formatRfc9457ErrorToBanner(err, locale, isFr ? "Gouvernance de l'espace" : "Workspace governance").fullText}`,
      );
    });
    return () => {
      cancelled = true;
    };
  }, [targetWsId, locale, isFr, reloadWaiversAndMechanisms]);

  if (!targetWorkspace) {
    return null;
  }

  const handleRegisterWaiver = async (sourceUri: string, conflictRuleId: string) => {
    if (!targetWsId || submitting) {
      return;
    }
    setSubmitting(true);
    const client = createOrciaApiClient({ baseUrl: "", locale });
    const reasonText = isFr
      ? "Dérogation locale validée par l'équipe de l'Espace."
      : "Local waiver approved by the Workspace team.";
    try {
      const saved = await client.registerWorkspaceExceptionWaiver(targetWsId, {
        source_uri: sourceUri,
        source_sha256: "sha256:workspace-source-baseline-0001",
        conflict_rule_id: conflictRuleId,
        norm_level: "3_WORKSPACE",
        dna_chain: [],
        reason: reasonText,
        ttl_days: 30,
      });
      const reloaded = await client.listWorkspaceExceptionWaivers(targetWsId, true);
      setActiveWaivers(
        reloaded.length > 0 ? reloaded.map(mapWaiverItem) : [mapWaiverItem(saved)],
      );
      onFeedback(
        isFr
          ? `✅ Dérogation enregistrée pour la règle « ${conflictRuleId} ».`
          : `✅ Waiver registered for rule "${conflictRuleId}".`,
      );
    } catch (err: unknown) {
      onFeedback(
        `⚠️ ${formatRfc9457ErrorToBanner(err, locale, isFr ? "Enregistrement de la dérogation" : "Waiver registration").fullText}`,
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleCompileFromNorm = async (ruleId: string) => {
    if (!targetWsId || submitting) {
      return;
    }
    setSubmitting(true);
    const client = createOrciaApiClient({ baseUrl: "", locale });
    try {
      const res = await client.compileDnaStarlark(targetWsId, {
        rule_id: ruleId,
        directive_title: "Orientation Qualité",
        norm_title: `Règle ${ruleId}`,
        natural_language_rule_fr:
          "Le champ reference_code doit être renseigné et conforme.",
        required_field: "reference_code",
      });
      const persisted = await client.listDnaMechanisms(targetWsId);
      setCompiledMechanism(
        persisted[0] ? mapMechanismItem(persisted[0]) : mapMechanismItem(res),
      );
      onFeedback(
        isFr
          ? `✅ Contrôle automatique généré et enregistré pour la règle « ${ruleId} ».`
          : `✅ Automated check generated and persisted for rule "${ruleId}".`,
      );
    } catch (err: unknown) {
      onFeedback(
        `⚠️ ${formatRfc9457ErrorToBanner(err, locale, isFr ? "Compilation de règle métier" : "Business rule compilation").fullText}`,
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleSignAndActivate = async (mechanismId: string) => {
    if (!targetWsId || submitting) {
      return;
    }
    setSubmitting(true);
    const client = createOrciaApiClient({ baseUrl: "", locale });
    try {
      const activated = await client.activateDnaMechanism(targetWsId, mechanismId);
      const persisted = await client.listDnaMechanisms(targetWsId);
      setCompiledMechanism(
        persisted[0] ? mapMechanismItem(persisted[0]) : mapMechanismItem(activated),
      );
      onFeedback(
        isFr
          ? "✅ Contrôle automatique signé et activé pour l'Espace de travail."
          : "✅ Automated check signed and activated for the Workspace.",
      );
    } catch (err: unknown) {
      onFeedback(
        `⚠️ ${formatRfc9457ErrorToBanner(err, locale, isFr ? "Activation de la règle" : "Rule activation").fullText}`,
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      data-testid="workspace-dna-and-waivers-section"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <WorkspaceFiveTabsAndExternalRebaseView
        workspaceSlug={targetWsSlug}
        workspaceName={targetWorkspace.name}
        ownerOrgUnitName={targetWorkspace.ownerOrgUnitName ?? null}
        visibilityLabel={formatWorkspaceVisibilityLabel(targetWorkspace.visibilityMode, isFr)}
        effectiveRoleLabel={formatWorkspaceAccessModeLabel(targetWorkspace.accessMode, isFr)}
        lifecyclePhaseLabel={formatWorkspacePhaseLabel(targetWorkspace.lifecyclePhase, isFr)}
        activeTab={activeSubTab}
        defaultArtifactDestinationUri={
          datasources[0]?.uri ?? `orcia://workspaces/${targetWsSlug}/artifacts`
        }
        pendingGlossaryCandidatesCount={
          ontologyConcepts.length + glossaryCandidates.length
        }
        sources={datasources.map((d) => ({
          sourceId: d.id,
          uri: d.uri,
          title: d.alias,
          authorityRole:
            d.scheme === "git" ? ("ACTIVE" as const) : ("REFERENCE" as const),
          accessMode: "READ_WRITE_TARGET" as const,
          freshnessStatus: "FRESH" as const,
        }))}
        activeWaivers={activeWaivers}
        rebasedChunks={[]}
        labels={dictionary.workspaceFiveTabs}
        submitting={submitting}
        onSelectTab={setActiveSubTab}
        onRegisterWaiver={(sourceUri, conflictRuleId) =>
          void handleRegisterWaiver(sourceUri, conflictRuleId)
        }
      />

      <DnaStarlarkCompilerAndGlossaryLifecycleView
        mechanism={compiledMechanism}
        pendingQueueCandidates={glossaryCandidates}
        top3PrecheckedCandidates={glossaryCandidates.slice(0, 3)}
        labels={dictionary.dnaStarlarkGlossary}
        submitting={submitting}
        onCompileFromNorm={(ruleId) => void handleCompileFromNorm(ruleId)}
        onSignAndActivate={(mechanismId) => void handleSignAndActivate(mechanismId)}
        onPromoteInFlow={(candidateIds) => {
          const promoted = glossaryCandidates.filter((c) =>
            candidateIds.includes(c.candidateId),
          );
          for (const item of promoted) {
            onAddOntologyConcept({
              conceptKey: item.candidateId,
              canonicalTerm: item.canonicalTerm,
              level: "3_WORKSPACE",
              scopeId: targetWsId || "scope-global",
              definitionText: item.definitionFr,
              immutable: false,
              synonyms: [],
              profileTranslations: {},
              impactedTemplates: [],
              impactedWorkflows: [],
              impactedRuns: [],
            });
          }
          setGlossaryCandidates((prev) =>
            prev.filter((c) => !candidateIds.includes(c.candidateId)),
          );
          onFeedback(
            isFr
              ? `✅ ${candidateIds.length} terme(s) validé(s) et intégré(s) au glossaire.`
              : `✅ ${candidateIds.length} term(s) approved and added to the glossary.`,
          );
        }}
        onRejectCandidate={(candidateId) => {
          setGlossaryCandidates((prev) =>
            prev.filter((c) => c.candidateId !== candidateId),
          );
          onFeedback(
            isFr
              ? "✅ Terme candidat écarté de la file d'attente."
              : "✅ Candidate term removed from queue.",
          );
        }}
      />
    </div>
  );
}
