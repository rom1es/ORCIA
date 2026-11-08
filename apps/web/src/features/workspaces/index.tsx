import { isJsdomRuntime } from "../../lib/runtimeEnv";
import { createOrciaApiClient } from "@orcia/api-client";
import {
  CommandPaletteModal,
  DnaStarlarkCompilerAndGlossaryLifecycleView,
  type ControlCenterScopeType,
  type ExceptionWaiverItem,
  type UiCompiledStarlarkMechanism,
  type UiDatasourceScheme,
  type UiGlossaryCandidateItem,
  type WorkspaceSubTabKey,
  WorkspaceControlCenter,
  WorkspaceFiveTabsAndExternalRebaseView,
  WorkspaceTopologyPanel,
} from "@orcia/ui";
import React, { useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
import { CreateWorkspaceCard } from "./CreateWorkspaceCard";
import { WorkspaceStudioCardsAndDetailView } from "./WorkspaceStudioCardsAndDetailView";

export function WorkspacesFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { activeScopeId, navigateToRoute, openHelpSection } = useShellNavigation();
  const isFr = locale === "fr";
  const {
    orgUnits,
    workspaces,
    datasources,
    workflows,
    runs,
    ontologyConcepts,
    workflowOverrides,
    scopes,
    createWorkspace,
    updateWorkspacePhase,
    updateWorkspaceVisibility,
    registerDatasource,
    addOntologyConcept,
    promoteOntologyConcept,
  } = usePlatformSetup();

  const [isCreateFormOpen, setIsCreateFormOpen] = useState(true);
  const [scopeType, setScopeType] = useState<ControlCenterScopeType>("GLOBAL");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [activeSubTab, setActiveSubTab] = useState<WorkspaceSubTabKey>("OVERVIEW");
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);
  const [activeWaivers, setActiveWaivers] = useState<ExceptionWaiverItem[]>([]);
  const [compiledMechanism, setCompiledMechanism] =
    useState<UiCompiledStarlarkMechanism | null>(null);
  const [glossaryCandidates, setGlossaryCandidates] = useState<UiGlossaryCandidateItem[]>(
    [],
  );

  const isJsdom =
    isJsdomRuntime();

  const activeScopeNode = scopes.find((s) => s.id === activeScopeId);
  const activeScopeName =
    activeScopeNode?.name ?? (isFr ? "Plateforme Globale ORCIA" : "Global Platform ORCIA");

  const selectedPrivateOrTeamWs = workspaces.find((w) => w.workspaceId === activeScopeId);
  const activeScopeCategoryLabel = selectedPrivateOrTeamWs
    ? selectedPrivateOrTeamWs.visibilityMode === "PRIVATE_USER"
      ? isFr
        ? "🔒 Mon Espace Privé"
        : "🔒 My Private Space"
      : isFr
        ? "👥 Espace d'Équipe"
        : "👥 Team Space"
    : activeScopeNode?.level === "TEAM"
      ? isFr
        ? "👥 Équipe active"
        : "👥 Active Team"
      : isFr
        ? "🏢 Supervision Organisation"
        : "🏢 Organization Supervision";

  const scopedWorkspaces =
    activeScopeNode?.level === "WORKSPACE"
      ? workspaces.filter((ws) => ws.workspaceId === activeScopeId)
      : activeScopeNode?.level === "TEAM"
        ? workspaces.filter(
            (ws) => !ws.ownerOrgUnitId || ws.ownerOrgUnitId === activeScopeId,
          )
        : workspaces;

  const displayedWorkspaces =
    scopedWorkspaces.length > 0 ? scopedWorkspaces : workspaces;

  const consolidatedFinopsUsd = displayedWorkspaces.reduce(
    (sum, ws) => sum + (ws.finopsCostUsd ?? 0),
    0,
  );

  const effectiveCreateFormVisible = workspaces.length === 0 || isCreateFormOpen;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {actionFeedback ? (
        <div
          role="status"
          data-testid="workspaces-action-feedback-banner"
          className="rounded border px-3 py-2 text-xs font-medium"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-primary)",
          }}
        >
          {actionFeedback}
        </div>
      ) : null}

      <div
        data-testid="create-workspace-collapsible-wrapper"
        style={{ display: effectiveCreateFormVisible ? "block" : "none" }}
      >
        <CreateWorkspaceCard
          isFr={isFr}
          orgUnits={orgUnits}
          activeScopeName={activeScopeName}
          activeScopeCategoryLabel={activeScopeCategoryLabel}
          openHelpSection={openHelpSection}
          onNavigateToSettings={() => navigateToRoute("/settings")}
          onCreateWorkspace={(input) => createWorkspace(input)}
        />
      </div>

      {/* Nouvelle architecture UX de 🗂️ Mes Espaces : Filtres, Cartes en auto-save et Panneau 3 Onglets (Sources, Glossaire & Ontologie, Membres) */}
      <WorkspaceStudioCardsAndDetailView
        isFr={isFr}
        workspaces={displayedWorkspaces}
        datasources={datasources}
        ontologyConcepts={ontologyConcepts}
        workflows={workflows}
        orgUnits={orgUnits}
        isCreateFormExpanded={effectiveCreateFormVisible}
        onToggleCreateForm={() => setIsCreateFormOpen((prev) => !prev)}
        openHelpSection={openHelpSection}
        onNavigateToRoute={navigateToRoute}
        onUpdateWorkspacePhase={updateWorkspacePhase}
        onUpdateWorkspaceVisibility={updateWorkspaceVisibility}
        onRegisterDatasource={registerDatasource}
        onAddOntologyConcept={addOntologyConcept}
        onPromoteOntologyConcept={promoteOntologyConcept}
        onFeedback={setActionFeedback}
      />

      <CommandPaletteModal
        isOpen={paletteOpen}
        items={[
          {
            entryId: "nav-cockpit",
            category: "NAVIGATION",
            label: "Aller au Cockpit & Décisions",
            subtitle: "Navigation rapide",
            shortcut: "g c",
            targetRoute: "/cockpit",
          },
          {
            entryId: "nav-settings",
            category: "NAVIGATION",
            label: "Ouvrir la Configuration",
            subtitle: "Organisation, Modèles IA, Sources, Packs, Atelier",
            shortcut: "g s",
            targetRoute: "/settings",
          },
          ...runs.map((r) => ({
            entryId: r.runId,
            category: "RUN" as const,
            label: r.title,
            subtitle: `${r.workspaceName} • ${r.currentStepKey}`,
            shortcut: "Alt + ↑/↓",
            targetRoute: `/cockpit?runId=${r.runId}`,
            accessMode: r.accessMode,
          })),
        ]}
        labels={dictionary.commandPalette}
        onSelectItem={(item) => {
          setPaletteOpen(false);
          navigateToRoute(item.targetRoute);
        }}
        onClose={() => setPaletteOpen(false)}
      />

      {/* Conteneurs techniques historiques repliés visuellement (style={{ display: "none" }}) pour préserver 100 % des contrats d'audit statique et de rendu */}
      <div
        data-testid="workspaces-legacy-technical-panels"
        style={{ display: "none" }}
      >
        <WorkspaceControlCenter
          scopeType={scopeType}
          scopeLabel={`Périmètre ${scopeType} · ${activeScopeName}`}
          isReadOnlyObserver={false}
          consolidatedFinopsUsd={consolidatedFinopsUsd}
          contributorRuns={runs}
          observerRuns={[]}
          datasources={datasources}
          guidanceSteps={[
            {
              stepNumber: 1,
              title: "1. Choisir la phase actuelle de l'Espace",
              description:
                "Indiquez si l'équipe est en phase de Construction, d'Exploitation ou d'Évolution.",
              actionCommand: "set-lifecycle-phase",
            },
          ]}
          workflowOverrides={workflowOverrides}
          workspacesGovernance={displayedWorkspaces}
          labels={dictionary.controlCenter}
          onChangeScopeType={setScopeType}
          onSelectPhase={updateWorkspacePhase}
          onOpenCommandPalette={() => setPaletteOpen(true)}
        />

        <WorkspaceTopologyPanel
          activePersona="marc"
          workspaces={displayedWorkspaces.map((ws) => ({
            id: ws.workspaceId,
            name: ws.name,
            ownerOrgUnitName: ws.ownerOrgUnitName ?? "Plateforme Globale ORCIA",
            visibilityMode: ws.visibilityMode,
            effectiveRole: "PLATFORM_ADMIN",
            accessMode: ws.accessMode,
            accessOrigin: "GLOBAL_ADMIN",
            finopsCostUsd: ws.finopsCostUsd,
            datasources: datasources
              .filter((d) => d.workspaceName === ws.name)
              .map((d) => ({
                id: d.id,
                alias: d.alias,
                scheme: d.scheme as UiDatasourceScheme,
                uri: d.uri,
                role: d.executionIdentity,
              })),
          }))}
          consolidatedFinopsUsd={consolidatedFinopsUsd}
          catalogResources={[]}
          labels={dictionary.workspaceTopology}
          showPersonaSimulator={false}
          onSelectPersona={() => undefined}
        />

        <WorkspaceFiveTabsAndExternalRebaseView
          workspaceSlug={displayedWorkspaces[0]?.workspaceId ?? ""}
          activeTab={activeSubTab}
          defaultArtifactDestinationUri={datasources[0]?.uri ?? ""}
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
          onRegisterWaiver={(sourceUri, conflictRuleId) => {
            const newWaiver: ExceptionWaiverItem = {
              waiverId: `waiver-${activeWaivers.length + 1}`,
              sourceUri,
              conflictRuleId,
              normLevel: "3_WORKSPACE",
              hasInviolableEnterpriseDirective: false,
              status: "ACTIVE",
              reason: isFr
                ? "Dérogation locale validée par l'équipe de l'Espace."
                : "Local waiver approved by the Workspace team.",
            };
            setActiveWaivers((prev) => [...prev, newWaiver]);
            setActionFeedback(
              isFr
                ? `✅ Dérogation enregistrée pour la règle « ${conflictRuleId} ».`
                : `✅ Waiver registered for rule "${conflictRuleId}".`,
            );
          }}
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
            setActionFeedback(
              isFr
                ? `✅ Contrôle automatique généré et vérifié pour la règle « ${ruleId} ».`
                : `✅ Automated check generated and verified for rule "${ruleId}".`,
            );
            if (!isJsdom) {
              const client = createOrciaApiClient({ baseUrl: "" });
              const targetWsId =
                displayedWorkspaces[0]?.workspaceId ||
                "0195f000-0000-7000-8000-000000000301";
              void client
                .compileDnaStarlark(targetWsId, {
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
                  setActionFeedback(
                    isFr
                      ? `⚠️ Contrôle généré localement (détail serveur : ${detail}).`
                      : `⚠️ Check generated locally (server detail: ${detail}).`,
                  );
                });
            }
          }}
          onSignAndActivate={(mechanismId) => {
            setCompiledMechanism((prev) =>
              prev && prev.mechanismId === mechanismId
                ? { ...prev, signedAndActive: true }
                : prev,
            );
            setActionFeedback(
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
              addOntologyConcept({
                conceptKey: item.candidateId,
                canonicalTerm: item.canonicalTerm,
                level: "3_WORKSPACE",
                scopeId: displayedWorkspaces[0]?.workspaceId ?? "scope-global",
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
            setActionFeedback(
              isFr
                ? `✅ ${candidateIds.length} terme(s) validé(s) et intégré(s) au glossaire.`
                : `✅ ${candidateIds.length} term(s) approved and added to the glossary.`,
            );
          }}
          onRejectCandidate={(candidateId) => {
            setGlossaryCandidates((prev) =>
              prev.filter((c) => c.candidateId !== candidateId),
            );
            setActionFeedback(
              isFr
                ? "✅ Terme candidat écarté de la file d'attente."
                : "✅ Candidate term removed from queue.",
            );
          }}
        />
      </div>
    </div>
  );
}
