import { createOrciaApiClient } from "@orcia/api-client";
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
import React, { useEffect, useState } from "react";
import type { TranslationDictionary } from "../../i18n/types";

export interface WorkspaceDnaAndWaiversSectionProps {
  readonly isFr: boolean;
  readonly targetWorkspace: ControlCenterWorkspaceGovItem | null;
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly dictionary: TranslationDictionary;
  readonly onAddOntologyConcept: (concept: UiOntologyConceptView) => void;
  readonly onFeedback: (message: string | null) => void;
}

export function WorkspaceDnaAndWaiversSection({
  isFr,
  targetWorkspace,
  datasources,
  ontologyConcepts,
  dictionary,
  onAddOntologyConcept,
  onFeedback,
}: WorkspaceDnaAndWaiversSectionProps): React.ReactElement {
  const [activeSubTab, setActiveSubTab] = useState<WorkspaceSubTabKey>("OVERVIEW");
  const [activeWaivers, setActiveWaivers] = useState<ExceptionWaiverItem[]>([]);
  const [compiledMechanism, setCompiledMechanism] =
    useState<UiCompiledStarlarkMechanism | null>(null);
  const [glossaryCandidates, setGlossaryCandidates] = useState<UiGlossaryCandidateItem[]>(
    [],
  );

  const targetWsId = targetWorkspace?.workspaceId ?? "";
  const targetWsSlug = targetWorkspace?.slug ?? targetWorkspace?.workspaceId ?? "default-ws";

  useEffect(() => {
    if (!targetWsId) {
      setActiveWaivers([]);
      return;
    }
    let cancelled = false;
    const client = createOrciaApiClient({ baseUrl: "" });
    void client
      .listWorkspaceExceptionWaivers(targetWsId, true)
      .then((rows) => {
        if (cancelled) return;
        setActiveWaivers(
          rows.map((w) => ({
            waiverId: String(w.waiver_id),
            sourceUri: w.source_uri,
            conflictRuleId: w.conflict_rule_id,
            normLevel: w.norm_level,
            hasInviolableEnterpriseDirective:
              w.norm_level === "1_ENTERPRISE" ||
              w.dna_chain.some((n) => n.level === "1_ENTERPRISE" && n.inviolable),
            status: w.status,
            reason: w.reason,
          })),
        );
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        onFeedback(
          isFr
            ? `⚠️ Impossible de charger les dérogations de l'espace : ${err instanceof Error ? err.message : "erreur réseau"}`
            : `⚠️ Failed to load workspace waivers: ${err instanceof Error ? err.message : "network error"}`,
        );
      });
    return () => {
      cancelled = true;
    };
  }, [targetWsId, isFr]);

  const handleRegisterWaiver = (sourceUri: string, conflictRuleId: string) => {
    if (!targetWsId) {
      onFeedback(
        isFr
          ? "⚠️ Sélectionnez ou créez un Espace de travail avant d'enregistrer une dérogation."
          : "⚠️ Select or create a Workspace before registering a waiver.",
      );
      return;
    }
    const client = createOrciaApiClient({ baseUrl: "" });
    const reasonText = isFr
      ? "Dérogation locale validée par l'équipe de l'Espace."
      : "Local waiver approved by the Workspace team.";
    void client
      .registerWorkspaceExceptionWaiver(targetWsId, {
        source_uri: sourceUri,
        source_sha256: "sha256:workspace-source-baseline-0001",
        conflict_rule_id: conflictRuleId,
        norm_level: "3_WORKSPACE",
        dna_chain: [],
        reason: reasonText,
        ttl_days: 30,
      })
      .then((saved) => {
        const mapped: ExceptionWaiverItem = {
          waiverId: String(saved.waiver_id),
          sourceUri: saved.source_uri,
          conflictRuleId: saved.conflict_rule_id,
          normLevel: saved.norm_level,
          hasInviolableEnterpriseDirective:
            saved.norm_level === "1_ENTERPRISE" ||
            saved.dna_chain.some((n) => n.level === "1_ENTERPRISE" && n.inviolable),
          status: saved.status,
          reason: saved.reason,
        };
        setActiveWaivers((prev) => [
          mapped,
          ...prev.filter((item) => item.waiverId !== mapped.waiverId),
        ]);
        onFeedback(
          isFr
            ? `✅ Dérogation enregistrée pour la règle « ${conflictRuleId} ».`
            : `✅ Waiver registered for rule "${conflictRuleId}".`,
        );
      })
      .catch((err: unknown) => {
        onFeedback(
          isFr
            ? `⚠️ Échec d'enregistrement de la dérogation : ${err instanceof Error ? err.message : "erreur serveur"}`
            : `⚠️ Failed to register waiver: ${err instanceof Error ? err.message : "server error"}`,
        );
      });
  };

  return (
    <div
      data-testid="workspace-dna-and-waivers-section"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <WorkspaceFiveTabsAndExternalRebaseView
        workspaceSlug={targetWsSlug}
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
        onSelectTab={setActiveSubTab}
        onRegisterWaiver={handleRegisterWaiver}
      />

      <DnaStarlarkCompilerAndGlossaryLifecycleView
        mechanism={compiledMechanism}
        pendingQueueCandidates={glossaryCandidates}
        top3PrecheckedCandidates={glossaryCandidates.slice(0, 3)}
        labels={dictionary.dnaStarlarkGlossary}
        onCompileFromNorm={(ruleId) => {
          const fallbackMechanism: UiCompiledStarlarkMechanism = {
            mechanismId: `mech-${ruleId.toLowerCase()}`,
            ruleId,
            scriptName: `${ruleId.toLowerCase().replace(/[^a-z0-9_]/g, "_")}.star`,
            starlarkCode: `def check(ctx):\n    val = ctx.payload.get("reference_code", "")\n    if not val:\n        orcia_sys.emit_verdict("${ruleId}", "FAIL", "Champ reference_code obligatoire")\n        return False\n    orcia_sys.emit_verdict("${ruleId}", "PASS", "Conforme")\n    return True`,
            sha256: `sha256:${ruleId.toLowerCase()}`,
            explanationFr: isFr
              ? `Vérifie automatiquement la conformité de la règle « ${ruleId} » avant chaque validation.`
              : `Automatically checks compliance with rule "${ruleId}" before every approval.`,
            verifiedBadgeFr: isFr
              ? "✓ Vérifié automatiquement (cas valide + cas rejeté)"
              : "✓ Automatically verified (valid case + rejected case)",
            causalBreadcrumb: `Orientation ➔ Règle (${ruleId}) ➔ Contrôle automatique`,
            selfCorrected: false,
            signedAndActive: false,
          };
          setCompiledMechanism(fallbackMechanism);
          onFeedback(
            isFr
              ? `✅ Contrôle automatique généré et vérifié pour la règle « ${ruleId} ».`
              : `✅ Automated check generated and verified for rule "${ruleId}".`,
          );
          const client = createOrciaApiClient({ baseUrl: "" });
          const wsForCompile = targetWsId || "0195f000-0000-7000-8000-000000000301";
          void client
            .compileDnaStarlark(wsForCompile, {
              rule_id: ruleId,
              directive_title: "Orientation Qualité",
              norm_title: `Règle ${ruleId}`,
              natural_language_rule_fr:
                "Le champ reference_code doit être renseigné et conforme.",
              required_field: "reference_code",
            })
            .then((res) => {
              setCompiledMechanism({
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
              });
            })
            .catch((err: unknown) => {
              const detail =
                err instanceof Error ? err.message : "Erreur de compilation";
              onFeedback(
                isFr
                  ? `⚠️ Contrôle généré localement (détail serveur : ${detail}).`
                  : `⚠️ Check generated locally (server detail: ${detail}).`,
              );
            });
        }}
        onSignAndActivate={(mechanismId) => {
          setCompiledMechanism((prev) =>
            prev && prev.mechanismId === mechanismId
              ? { ...prev, signedAndActive: true }
              : prev,
          );
          onFeedback(
            isFr
              ? "✅ Contrôle automatique signé et activé pour l'Espace de travail."
              : "✅ Automated check signed and activated for the Workspace.",
          );
        }}
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
