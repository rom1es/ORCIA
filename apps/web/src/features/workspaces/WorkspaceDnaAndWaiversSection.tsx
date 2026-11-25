import {
  DnaStarlarkCompilerAndGlossaryLifecycleView,
  type ControlCenterRunItem,
  type ControlCenterWorkspaceGovItem,
  type UiOntologyConceptView,
  type UiOntologyLevel,
  type WorkspaceDeliverableItem,
  type WorkspaceSubTabKey,
  type WorkspaceVisibilityMode,
  WorkspaceFiveTabsAndExternalRebaseView,
} from "@orcia/ui";
import React, { useEffect, useRef, useState } from "react";
import type { ConfiguredOrgUnit } from "../../components/platformSetupStore";
import { formatI18nTemplate, resolveDictionaryForFlag } from "../../i18n";
import type { TranslationDictionary } from "../../i18n/types";
import { useWorkspaceDnaAndWaivers } from "./useWorkspaceDnaAndWaivers";
import { WorkspaceGlossaryAndOntologyTab } from "./WorkspaceGlossaryAndOntologyTab";
import { WorkspaceMembersAndSettingsTab } from "./WorkspaceMembersAndSettingsTab";
import { WorkspaceSourcesRagTab } from "./WorkspaceSourcesRagTab";
import {
  formatWorkspaceDisplaySlug,
  resolveWorkspacePhaseLabel,
  resolveWorkspaceVisibilityMeta,
  sanitizeWorkspaceDestinationUri,
  toKebabWorkspaceSlug,
} from "./workspaceDisplayHelpers";
import type { WorkspaceFeedbackInput } from "./workspaceFeedbackTypes";

export interface WorkspaceDnaAndWaiversSectionProps {
  readonly isFr: boolean;
  readonly initialTab?: string;
  readonly targetWorkspace: ControlCenterWorkspaceGovItem | null;
  readonly runs?: readonly ControlCenterRunItem[];
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly dictionary: TranslationDictionary;
  readonly openHelpSection: (sectionId: string) => void;
  readonly onAddOntologyConcept: (concept: UiOntologyConceptView) => void;
  readonly onPromoteOntologyConcept: (
    conceptKey: string,
    targetLevel: UiOntologyLevel,
    targetScopeId?: string,
  ) => void;
  readonly onUpdateWorkspaceVisibility?: (
    workspaceId: string,
    visibilityMode: WorkspaceVisibilityMode,
  ) => void | Promise<void>;
  readonly onMarkAutosaved?: (workspaceId: string) => void;
  readonly onFeedback: (feedback: WorkspaceFeedbackInput) => void;
}

export function resolveInitialWorkspaceSubTab(initialTab?: string): WorkspaceSubTabKey {
  switch ((initialTab ?? "").trim().toLowerCase()) {
    case "sources":
    case "documents_sources":
      return "DOCUMENTS_SOURCES";
    case "deliverables":
    case "deliverables_artifacts":
      return "DELIVERABLES_ARTIFACTS";
    case "glossary":
    case "glossary_rules":
      return "GLOSSARY_RULES";
    case "members":
    case "members_team":
      return "MEMBERS_TEAM";
    default:
      return "OVERVIEW";
  }
}

function formatWorkspaceAccessModeLabel(accessMode: string | undefined, isFr: boolean): string {
  const dnaCopy = resolveDictionaryForFlag(isFr).featureWorkspaces.dnaAndWaivers;
  return accessMode === "READ_ONLY_OBSERVER"
    ? dnaCopy.accessReadOnly
    : dnaCopy.accessContributor;
}

export function WorkspaceDnaAndWaiversSection({
  isFr,
  initialTab,
  targetWorkspace,
  runs = [],
  ontologyConcepts,
  orgUnits,
  dictionary,
  openHelpSection,
  onAddOntologyConcept,
  onPromoteOntologyConcept,
  onUpdateWorkspaceVisibility,
  onMarkAutosaved,
  onFeedback,
}: WorkspaceDnaAndWaiversSectionProps): React.ReactElement | null {
  const [activeSubTab, setActiveSubTab] = useState<WorkspaceSubTabKey>(() =>
    resolveInitialWorkspaceSubTab(initialTab),
  );
  const [glossaryRefreshNonce, setGlossaryRefreshNonce] = useState<number>(0);
  const prevInitialTabRef = useRef(initialTab);

  useEffect(() => {
    if (prevInitialTabRef.current !== initialTab) {
      prevInitialTabRef.current = initialTab;
      setActiveSubTab(resolveInitialWorkspaceSubTab(initialTab));
    }
  }, [initialTab]);

  const {
    activeWaivers,
    compiledMechanism,
    scopedDatasources,
    setScopedDatasources,
    glossaryCandidates,
    submitting,
    reloadGovernanceState,
    handleRegisterWaiver,
    handleCompileFromNorm,
    handleSignAndActivate,
    handlePromoteInFlow,
    handleRejectCandidate,
  } = useWorkspaceDnaAndWaivers({
    isFr,
    targetWorkspace,
    onFeedback,
    onGlossaryMutated: () => setGlossaryRefreshNonce((n) => n + 1),
  });

  if (!targetWorkspace) {
    return null;
  }

  const targetWsId = targetWorkspace.workspaceId;
  const displayWsSlug = formatWorkspaceDisplaySlug(targetWorkspace);
  const defaultDestinationUri = scopedDatasources[0]?.uri
    ? sanitizeWorkspaceDestinationUri(scopedDatasources[0].uri, targetWorkspace.name)
    : `orcia://workspaces/${displayWsSlug}/deliverables`;
  const tabsCopy = dictionary.featureWorkspaces.detailTabs;

  const scopedDeliverables: readonly WorkspaceDeliverableItem[] = runs
    .filter((r) => r.workspaceId === targetWsId)
    .map((r) => ({
      deliverableId: r.runId,
      title: r.title,
      casUri: `orcia://workspaces/${displayWsSlug}/artifacts/${toKebabWorkspaceSlug(r.title)}@v1`,
      versionLabel: "@v1",
      status: r.status,
    }));

  return (
    <div
      data-testid="workspace-dna-and-waivers-section"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <WorkspaceFiveTabsAndExternalRebaseView
        workspaceSlug={displayWsSlug}
        workspaceName={targetWorkspace.name}
        ownerOrgUnitName={targetWorkspace.ownerOrgUnitName ?? null}
        visibilityLabel={resolveWorkspaceVisibilityMeta(targetWorkspace.visibilityMode, isFr).fullLabel}
        effectiveRoleLabel={formatWorkspaceAccessModeLabel(targetWorkspace.accessMode, isFr)}
        lifecyclePhaseLabel={resolveWorkspacePhaseLabel(targetWorkspace.lifecyclePhase, isFr)}
        activeTab={activeSubTab}
        defaultArtifactDestinationUri={defaultDestinationUri}
        pendingGlossaryCandidatesCount={glossaryCandidates.length}
        sources={scopedDatasources.map((d) => ({
          sourceId: d.id,
          uri: d.uri,
          title: d.alias,
          authorityRole:
            d.codegraph_enabled || d.source_nature === "SOURCE_CODE"
              ? ("ACTIVE" as const)
              : ("REFERENCE" as const),
          accessMode: "READ_WRITE_TARGET" as const,
          freshnessStatus:
            d.freshness_status === "STALE" || d.freshness_status === "SYNC_ERROR"
              ? ("STALE_WARNING" as const)
              : ("FRESH" as const),
        }))}
        activeWaivers={activeWaivers}
        deliverables={scopedDeliverables}
        rebasedChunks={[]}
        labels={dictionary.workspaceFiveTabs}
        submitting={submitting}
        onSelectTab={setActiveSubTab}
        onRegisterWaiver={(sourceUri, conflictRuleId) =>
          void handleRegisterWaiver(sourceUri, conflictRuleId)
        }
        sourcesTabSlot={
          <WorkspaceSourcesRagTab
            isFr={isFr}
            activeWorkspace={targetWorkspace}
            initialDatasources={scopedDatasources}
            openHelpSection={openHelpSection}
            onSourcesChanged={setScopedDatasources}
            onFeedback={onFeedback}
          />
        }
        glossaryTabSlot={
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <WorkspaceGlossaryAndOntologyTab
              isFr={isFr}
              selectedWorkspace={targetWorkspace}
              orgUnits={orgUnits}
              ontologyConcepts={ontologyConcepts}
              refreshNonce={glossaryRefreshNonce}
              openHelpSection={openHelpSection}
              onAddConcept={(concept) => {
                onAddOntologyConcept(concept);
                onFeedback(
                  formatI18nTemplate(tabsCopy.termAddedTemplate, { term: concept.canonicalTerm }),
                );
              }}
              onPromoteConcept={(conceptKey, targetLevel, targetScopeId) => {
                onPromoteOntologyConcept(conceptKey, targetLevel, targetScopeId);
                onFeedback(tabsCopy.termPromoted);
              }}
              onPromotionsChanged={() => void reloadGovernanceState()}
              onFeedback={onFeedback}
            />
            <DnaStarlarkCompilerAndGlossaryLifecycleView
              mechanism={compiledMechanism}
              pendingQueueCandidates={glossaryCandidates}
              top3PrecheckedCandidates={glossaryCandidates.slice(0, 3)}
              labels={dictionary.dnaStarlarkGlossary}
              submitting={submitting}
              onCompileFromNorm={(ruleId) => void handleCompileFromNorm(ruleId)}
              onSignAndActivate={(mechanismId) => void handleSignAndActivate(mechanismId)}
              onPromoteInFlow={(candidateIds) => void handlePromoteInFlow(candidateIds)}
              onRejectCandidate={(candidateId) => void handleRejectCandidate(candidateId)}
            />
          </div>
        }
        membersTabSlot={
          <WorkspaceMembersAndSettingsTab
            isFr={isFr}
            activeWorkspace={targetWorkspace}
            orgUnits={orgUnits}
            onUpdateWorkspaceVisibility={onUpdateWorkspaceVisibility}
            onMarkAutosaved={onMarkAutosaved}
            onFeedback={onFeedback}
          />
        }
      />
    </div>
  );
}
