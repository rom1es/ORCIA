import type {
  ControlCenterWorkspaceGovItem,
  UiCatalogExplorerItemView,
  UiOntologyConceptView,
  UiOntologyLevel,
} from "@orcia/ui";
import {
  deduplicateConfiguredPacks,
  formatHumanReadableScopePath,
  type ConfiguredAuditEvent,
  type ConfiguredOrgUnit,
  type ConfiguredPackItem,
  type ConfiguredPlatformAdmin,
  type ConfiguredRbacGrant,
  type ConfiguredWorkflowItem,
} from "./platformSetupStorageHelpers";

export type AppendAuditFn = (
  eventType: string,
  summary: string,
  meta?: {
    readonly actorName?: string;
    readonly actorEmail?: string;
    readonly scopeId?: string;
    readonly scopePath?: string;
    readonly scopeLabel?: string;
  },
) => readonly ConfiguredAuditEvent[];

export function computeRemoveOrgUnitOutcome(params: {
  readonly orgUnitId: string;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly rbacGrants: readonly ConfiguredRbacGrant[];
  readonly platformAdmin: ConfiguredPlatformAdmin | null;
  readonly appendAudit: AppendAuditFn;
}): {
  readonly deleted: boolean;
  readonly blockedReason: string | null;
  readonly nextOrgUnits?: readonly ConfiguredOrgUnit[];
  readonly updatedAdmin?: ConfiguredPlatformAdmin;
  readonly nextAudit?: readonly ConfiguredAuditEvent[];
} {
  const { orgUnitId, orgUnits, workspaces, rbacGrants, platformAdmin, appendAudit } = params;
  const target = orgUnits.find((u) => u.id === orgUnitId);
  if (!target) {
    return { deleted: false, blockedReason: null };
  }
  const childUnits = orgUnits.filter((u) => u.parentId === target.id);
  if (childUnits.length > 0) {
    const childLabel =
      childUnits.length > 1
        ? `${childUnits.length} Équipes sont rattachées`
        : "1 Équipe est rattachée";
    return {
      deleted: false,
      blockedReason: `Suppression refusée : ${childLabel} à « ${target.name} » (${childUnits.map((c) => c.name).join(", ")}). Supprimez ou détachez d'abord les éléments enfants pour éviter toute configuration orpheline.`,
    };
  }
  const attachedWorkspaces = workspaces.filter((w) => w.ownerOrgUnitId === target.id);
  if (attachedWorkspaces.length > 0) {
    const wsLabel =
      attachedWorkspaces.length > 1
        ? `${attachedWorkspaces.length} Espaces de Travail sont rattachés`
        : "1 Espace de Travail est rattaché";
    return {
      deleted: false,
      blockedReason: `Suppression refusée : ${wsLabel} à « ${target.name} » (${attachedWorkspaces.map((w) => w.name).join(", ")}). Supprimez ou réattribuez d'abord ces espaces.`,
    };
  }
  const dependentGrants = rbacGrants.filter(
    (g) =>
      g.scopePath === target.slug ||
      g.scopePath === target.name ||
      g.scopePath.includes(`/${target.slug}`) ||
      g.scopePath.startsWith(`${target.slug}/`),
  );
  if (dependentGrants.length > 0) {
    const grantLabel =
      dependentGrants.length > 1
        ? `${dependentGrants.length} règles d'habilitation ciblent`
        : "1 règle d'habilitation cible";
    return {
      deleted: false,
      blockedReason: `Suppression refusée : ${grantLabel} « ${target.name} ». Supprimez d'abord ces habilitations pour ne pas laisser de configuration orpheline.`,
    };
  }
  const nextOrgUnits = orgUnits.filter((u) => u.id !== orgUnitId);
  const updatedAdmin =
    platformAdmin?.memberTeamIds?.includes(orgUnitId)
      ? {
          ...platformAdmin,
          memberTeamIds: platformAdmin.memberTeamIds.filter((id) => id !== orgUnitId),
        }
      : undefined;
  const levelLabel = target.level === "BU" ? "Direction (BU)" : "Équipe";
  const nextAudit = appendAudit(
    "OrgUnitDeleted",
    `${levelLabel} "${target.name}" (${target.slug}) supprimée`,
    {
      scopeId: target.id,
      scopePath: target.slug,
      scopeLabel: `${levelLabel} · ${target.name}`,
    },
  );
  return {
    deleted: true,
    blockedReason: null,
    nextOrgUnits,
    ...(updatedAdmin ? { updatedAdmin } : {}),
    nextAudit,
  };
}

export function applyRegisterPack(params: {
  readonly packs: readonly ConfiguredPackItem[];
  readonly catalogItems: readonly UiCatalogExplorerItemView[];
  readonly input: ConfiguredPackItem;
  readonly appendAudit: AppendAuditFn;
}): {
  readonly nextPacks: readonly ConfiguredPackItem[];
  readonly nextCatalogItems: readonly UiCatalogExplorerItemView[];
  readonly nextAudit: readonly ConfiguredAuditEvent[];
} {
  const { packs, catalogItems, input, appendAudit } = params;
  const nextPacks = deduplicateConfiguredPacks([
    ...packs.filter(
      (p) =>
        !(
          p.packKey === input.packKey &&
          (p.scopePath === input.scopePath || input.scopePath === "GLOBAL")
        ),
    ),
    input,
  ]);
  const nextCatalogItems: readonly UiCatalogExplorerItemView[] = [
    ...catalogItems.filter((item) => item.resourceId !== `pack-${input.packKey}`),
    {
      resourceId: `pack-${input.packKey}`,
      uri: `orcia://packs/${input.packKey}@${input.version}`,
      scheme: "orcia",
      title: input.packKey,
      description: `Pack ${input.packKey} (${input.status})`,
      resourceType: "workflow",
      sourceFormat: "ORCIA",
      version: input.version,
      sha256Short: "e3b0c44298fc", // pragma: allowlist secret
      casKey: "cas/e3b0c44298fc", // pragma: allowlist secret
      visibilityScope: "PUBLISHED_ORG",
      grantedPermissions: ["DISCOVER", "EXECUTE"],
      sourceMasked: false,
    },
  ];
  const readableScope = formatHumanReadableScopePath(input.scopePath);
  const nextAudit = appendAudit(
    "PackRegistered",
    `Pack "${input.packKey}@${input.version}" activé sur ${readableScope}`,
    {
      scopePath: input.scopePath,
      scopeLabel: readableScope,
    },
  );
  return { nextPacks, nextCatalogItems, nextAudit };
}

export function applyUpsertWorkflow(params: {
  readonly workflows: readonly ConfiguredWorkflowItem[];
  readonly catalogItems: readonly UiCatalogExplorerItemView[];
  readonly input: ConfiguredWorkflowItem;
  readonly appendAudit: AppendAuditFn;
}): {
  readonly nextWorkflows: readonly ConfiguredWorkflowItem[];
  readonly nextCatalogItems: readonly UiCatalogExplorerItemView[];
  readonly nextAudit: readonly ConfiguredAuditEvent[];
} {
  const { workflows, catalogItems, input, appendAudit } = params;
  const nextWorkflows = [
    ...workflows.filter((w) => w.workflowKey !== input.workflowKey),
    input,
  ];
  const nextCatalogItems: readonly UiCatalogExplorerItemView[] = [
    ...catalogItems.filter((item) => item.resourceId !== `wf-${input.workflowKey}`),
    {
      resourceId: `wf-${input.workflowKey}`,
      uri: `orcia://workflows/${input.workflowKey}@${input.version}`,
      scheme: "orcia",
      title: input.title,
      description: input.prePrompt || input.title,
      resourceType: "workflow",
      sourceFormat: "ORCIA",
      version: input.version,
      sha256Short: input.prePromptSha256.slice(0, 12),
      casKey: `cas/${input.prePromptSha256.slice(0, 12)}`,
      visibilityScope: "SHARED_WORKSPACE",
      grantedPermissions: ["DISCOVER", "EXECUTE", "EDIT"],
      sourceMasked: false,
    },
  ];
  const statusLabel = input.status === "PUBLISHED" ? "Publié" : "Brouillon";
  const nextAudit = appendAudit(
    "WorkflowSaved",
    `Processus "${input.title || input.workflowKey}" (${statusLabel}) enregistré`,
    {
      scopeId: "scope-global",
      scopePath: "GLOBAL",
      scopeLabel: "Plateforme entière",
    },
  );
  return { nextWorkflows, nextCatalogItems, nextAudit };
}

export function formatOntologyLevelLabel(level: UiOntologyLevel): string {
  if (level === "1_ENTERPRISE") return "Entreprise (Global)";
  if (level === "2_DOMAIN") return "Direction (BU)";
  if (level === "3_TEAM") return "Équipe";
  return "Espace de travail";
}

export function applyPromoteOntologyConcept(params: {
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly conceptKey: string;
  readonly targetLevel: UiOntologyLevel;
  readonly targetScopeId?: string;
  readonly appendAudit: AppendAuditFn;
}): {
  readonly nextConcepts: readonly UiOntologyConceptView[];
  readonly nextAudit: readonly ConfiguredAuditEvent[];
} | null {
  const { ontologyConcepts, conceptKey, targetLevel, targetScopeId, appendAudit } = params;
  const targetConcept = ontologyConcepts.find((c) => c.conceptKey === conceptKey);
  if (!targetConcept) return null;
  const nextScopeId =
    targetScopeId ??
    (targetLevel === "1_ENTERPRISE" ? "scope-global" : targetConcept.scopeId);
  const nextConcepts = ontologyConcepts.map((c) =>
    c.conceptKey === conceptKey
      ? {
          ...c,
          level: targetLevel,
          scopeId: nextScopeId,
          immutable: targetLevel === "1_ENTERPRISE",
        }
      : c,
  );
  const nextAudit = appendAudit(
    "OntologyConceptCreated",
    `Terme métier "${targetConcept.canonicalTerm}" promu au niveau ${formatOntologyLevelLabel(targetLevel)}`,
    {
      scopeId: nextScopeId,
      scopePath: nextScopeId,
      scopeLabel: formatHumanReadableScopePath(nextScopeId),
    },
  );
  return { nextConcepts, nextAudit };
}
