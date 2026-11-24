import type {
  ControlCenterRunItem,
  UiCatalogExplorerItemView,
  UiOntologyConceptView,
  UiOntologyLevel,
} from "@orcia/ui";
import { DICTIONARIES, formatI18nTemplate, type SupportedWebLocale } from "../i18n";
import {
  applyPromoteOntologyConcept,
  applyRegisterPack,
  applyUpsertWorkflow,
  formatOntologyLevelLabel,
  type AppendAuditFn,
} from "./platformSetupOrgAndGovernance";
import {
  formatHumanReadableScopePath,
  type CachedPlatformSetupState,
  type ConfiguredAuditEvent,
  type ConfiguredPackItem,
  type ConfiguredWorkflowItem,
} from "./platformSetupStorageHelpers";

export interface CatalogAndRunActionsDeps {
  readonly locale: SupportedWebLocale;
  readonly packs: readonly ConfiguredPackItem[];
  readonly workflows: readonly ConfiguredWorkflowItem[];
  readonly runs: readonly ControlCenterRunItem[];
  readonly catalogItems: readonly UiCatalogExplorerItemView[];
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly setPacks: (packs: readonly ConfiguredPackItem[]) => void;
  readonly setWorkflows: (workflows: readonly ConfiguredWorkflowItem[]) => void;
  readonly setRuns: (runs: readonly ControlCenterRunItem[]) => void;
  readonly setCatalogItems: (items: readonly UiCatalogExplorerItemView[]) => void;
  readonly setOntologyConcepts: (concepts: readonly UiOntologyConceptView[]) => void;
  readonly setAuditEvents: (events: readonly ConfiguredAuditEvent[]) => void;
  readonly appendAudit: AppendAuditFn;
  readonly buildSnapshot: (
    overrides: Partial<CachedPlatformSetupState>,
  ) => CachedPlatformSetupState;
  readonly persistSnapshot: (next: CachedPlatformSetupState) => void;
}

export function createPlatformCatalogAndRunActions(deps: CatalogAndRunActionsDeps) {
  const {
    locale,
    packs,
    workflows,
    runs,
    catalogItems,
    ontologyConcepts,
    setPacks,
    setWorkflows,
    setRuns,
    setCatalogItems,
    setOntologyConcepts,
    setAuditEvents,
    appendAudit,
    buildSnapshot,
    persistSnapshot,
  } = deps;
  const copy = DICTIONARIES[locale].shellChrome.platformSetupGovernance;

  const registerPack = (input: ConfiguredPackItem) => {
    const { nextPacks, nextCatalogItems, nextAudit } = applyRegisterPack({
      packs,
      catalogItems,
      input,
      appendAudit,
    });
    setPacks(nextPacks);
    setCatalogItems(nextCatalogItems);
    setAuditEvents(nextAudit);
    persistSnapshot(
      buildSnapshot({ packs: nextPacks, catalogItems: nextCatalogItems, auditEvents: nextAudit }),
    );
  };

  const removePack = (packKey: string, scopePath?: string) => {
    const nextPacks = packs.filter(
      (p) => !(p.packKey === packKey && (scopePath === undefined || p.scopePath === scopePath)),
    );
    const stillActiveSomewhere = nextPacks.some((p) => p.packKey === packKey);
    const nextCatalogItems = stillActiveSomewhere
      ? catalogItems
      : catalogItems.filter((item) => item.resourceId !== `pack-${packKey}`);
    const readableScope = formatHumanReadableScopePath(scopePath ?? "GLOBAL", locale);
    const nextAudit = appendAudit(
      "PackDeactivated",
      formatI18nTemplate(copy.packDeactivatedTemplate, { packKey, scope: readableScope }),
      { scopePath: scopePath ?? "GLOBAL", scopeLabel: readableScope },
    );
    setPacks(nextPacks);
    setCatalogItems(nextCatalogItems);
    setAuditEvents(nextAudit);
    persistSnapshot(
      buildSnapshot({ packs: nextPacks, catalogItems: nextCatalogItems, auditEvents: nextAudit }),
    );
  };

  const upsertWorkflow = (input: ConfiguredWorkflowItem) => {
    const { nextWorkflows, nextCatalogItems, nextAudit } = applyUpsertWorkflow({
      workflows,
      catalogItems,
      input,
      appendAudit,
    });
    setWorkflows(nextWorkflows);
    setCatalogItems(nextCatalogItems);
    setAuditEvents(nextAudit);
    persistSnapshot(
      buildSnapshot({ workflows: nextWorkflows, catalogItems: nextCatalogItems, auditEvents: nextAudit }),
    );
  };

  const launchRun = (input: {
    workspaceId: string;
    workspaceName: string;
    title: string;
    workflowKey: string;
  }) => {
    const runId = `run-${runs.length + 1}`;
    const nextRuns: readonly ControlCenterRunItem[] = [
      ...runs,
      {
        runId,
        workspaceId: input.workspaceId,
        workspaceName: input.workspaceName,
        title: input.title,
        status: "RUNNING",
        currentStepKey: input.workflowKey,
        executionMode: "COACHING",
        accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
        budgetConsumedUsd: 0,
        blackboardSummary: copy.userLaunchedSummary,
      },
    ];
    const nextAudit = appendAudit(
      "RunLaunched",
      formatI18nTemplate(copy.runLaunchedTemplate, {
        title: input.title,
        runId,
        workspaceName: input.workspaceName,
      }),
      {
        scopeId: input.workspaceId,
        scopePath: input.workspaceName,
        scopeLabel: formatI18nTemplate(copy.spaceScopePrefix, { name: input.workspaceName }),
      },
    );
    setRuns(nextRuns);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ runs: nextRuns, auditEvents: nextAudit }));
  };

  const addOntologyConcept = (input: UiOntologyConceptView) => {
    const nextConcepts = [...ontologyConcepts, input];
    const nextAudit = appendAudit(
      "OntologyConceptCreated",
      formatI18nTemplate(copy.ontologyConceptCreatedTemplate, {
        term: input.canonicalTerm,
        level: formatOntologyLevelLabel(input.level),
      }),
      {
        scopeId: input.scopeId || "scope-global",
        scopePath: input.scopeId || "GLOBAL",
        scopeLabel: formatHumanReadableScopePath(input.scopeId || "GLOBAL", locale),
      },
    );
    setOntologyConcepts(nextConcepts);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ ontologyConcepts: nextConcepts, auditEvents: nextAudit }));
  };

  const promoteOntologyConcept = (
    conceptKey: string,
    targetLevel: UiOntologyLevel,
    targetScopeId?: string,
  ) => {
    const outcome = applyPromoteOntologyConcept({
      ontologyConcepts,
      conceptKey,
      targetLevel,
      ...(targetScopeId !== undefined ? { targetScopeId } : {}),
      appendAudit,
    });
    if (!outcome) return;
    setOntologyConcepts(outcome.nextConcepts);
    setAuditEvents(outcome.nextAudit);
    persistSnapshot(
      buildSnapshot({ ontologyConcepts: outcome.nextConcepts, auditEvents: outcome.nextAudit }),
    );
  };

  return {
    registerPack,
    removePack,
    upsertWorkflow,
    launchRun,
    addOntologyConcept,
    promoteOntologyConcept,
  };
}
