import {
  DnaStarlarkCompilerAndGlossaryLifecycleView,
  type ControlCenterDatasourceItem,
  type ControlCenterWorkspaceGovItem,
  type UiOntologyConceptView,
  type UiOntologyLevel,
  type WorkspaceSubTabKey,
  WorkspaceFiveTabsAndExternalRebaseView,
} from "@orcia/ui";
import React, { useEffect, useRef, useState } from "react";
import type {
  ConfiguredOrgUnit,
  PlatformSetupContextValue,
} from "../../components/platformSetupStore";
import { formatI18nTemplate, resolveDictionaryForFlag } from "../../i18n";
import type { TranslationDictionary } from "../../i18n/types";
import { useWorkspaceDnaAndWaivers } from "./useWorkspaceDnaAndWaivers";
import { WorkspaceGlossaryAndOntologyTab } from "./WorkspaceGlossaryAndOntologyTab";
import { WorkspaceMembersInstructionsCard } from "./WorkspaceMembersInstructionsCard";
import { WorkspaceSourcesRagTab } from "./WorkspaceSourcesRagTab";
import {
  formatWorkspaceDisplaySlug,
  resolveWorkspacePhaseLabel,
  resolveWorkspaceVisibilityMeta,
  sanitizeWorkspaceDestinationUri,
} from "./workspaceDisplayHelpers";

export interface WorkspaceDnaAndWaiversSectionProps {
  readonly isFr: boolean;
  readonly initialTab?: string;
  readonly targetWorkspace: ControlCenterWorkspaceGovItem | null;
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly dictionary: TranslationDictionary;
  readonly openHelpSection: (sectionId: string) => void;
  readonly onRegisterDatasource: PlatformSetupContextValue["registerDatasource"];
  readonly onAddOntologyConcept: (concept: UiOntologyConceptView) => void;
  readonly onPromoteOntologyConcept: (
    conceptKey: string,
    targetLevel: UiOntologyLevel,
    targetScopeId?: string,
  ) => void;
  readonly onFeedback: (message: string | null) => void;
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
  datasources,
  ontologyConcepts,
  orgUnits,
  dictionary,
  openHelpSection,
  onRegisterDatasource,
  onAddOntologyConcept,
  onPromoteOntologyConcept,
  onFeedback,
}: WorkspaceDnaAndWaiversSectionProps): React.ReactElement | null {
  const [activeSubTab, setActiveSubTab] = useState<WorkspaceSubTabKey>(() =>
    resolveInitialWorkspaceSubTab(initialTab),
  );
  const prevInitialTabRef = useRef(initialTab);

  useEffect(() => {
    if (prevInitialTabRef.current !== initialTab) {
      prevInitialTabRef.current = initialTab;
      setActiveSubTab(resolveInitialWorkspaceSubTab(initialTab));
    }
  }, [initialTab]);

  const {
    dnaCopy,
    activeWaivers,
    compiledMechanism,
    glossaryCandidates,
    setGlossaryCandidates,
    submitting,
    handleRegisterWaiver,
    handleCompileFromNorm,
    handleSignAndActivate,
  } = useWorkspaceDnaAndWaivers({ isFr, targetWorkspace, onFeedback });

  if (!targetWorkspace) {
    return null;
  }

  const targetWsId = targetWorkspace.workspaceId;
  const displayWsSlug = formatWorkspaceDisplaySlug(targetWorkspace);
  const defaultDestinationUri = datasources[0]?.uri
    ? sanitizeWorkspaceDestinationUri(datasources[0].uri, targetWorkspace.name)
    : `orcia://workspaces/${displayWsSlug}/deliverables`;
  const tabsCopy = dictionary.featureWorkspaces.detailTabs;

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
        pendingGlossaryCandidatesCount={ontologyConcepts.length + glossaryCandidates.length}
        sources={datasources.map((d) => ({
          sourceId: d.id,
          uri: d.uri,
          title: d.alias,
          authorityRole: d.scheme === "git" ? ("ACTIVE" as const) : ("REFERENCE" as const),
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
        sourcesTabSlot={
          <WorkspaceSourcesRagTab
            isFr={isFr}
            activeWorkspace={targetWorkspace}
            fallbackDatasources={datasources}
            openHelpSection={openHelpSection}
            onRegisterDatasource={onRegisterDatasource}
            onFeedback={onFeedback}
          />
        }
        glossaryTabSlot={
          <WorkspaceGlossaryAndOntologyTab
            isFr={isFr}
            selectedWorkspace={targetWorkspace}
            orgUnits={orgUnits}
            ontologyConcepts={ontologyConcepts}
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
          />
        }
        membersTabSlot={
          <WorkspaceMembersInstructionsCard isFr={isFr} activeWorkspace={targetWorkspace} />
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
            formatI18nTemplate(dnaCopy.candidatesApprovedTemplate, {
              count: candidateIds.length,
            }),
          );
        }}
        onRejectCandidate={(candidateId) => {
          setGlossaryCandidates((prev) =>
            prev.filter((c) => c.candidateId !== candidateId),
          );
          onFeedback(dnaCopy.candidateRejectedBanner);
        }}
      />
    </div>
  );
}
