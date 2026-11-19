import type { StatusBadgeTone, UiActivityScopeFilterOption } from "@orcia/ui";
import { formatShortDateTime } from "../lib/formatters";

export const EVENT_TYPE_FR_LABELS: Record<string, { label: string; tone: StatusBadgeTone }> = {
  PlatformAdminInitialized: { label: "Administrateur initialisé", tone: "emerald" },
  OrgUnitCreated: { label: "Unité d'organisation créée", tone: "cobalt" },
  OrgUnitDeleted: { label: "Unité d'organisation supprimée", tone: "amber" },
  PermissionGranted: { label: "Habilitation attribuée", tone: "emerald" },
  PermissionRevoked: { label: "Habilitation révoquée", tone: "amber" },
  RbacGrantCreated: { label: "Habilitation attribuée", tone: "emerald" },
  SettingsChanged: { label: "Paramètre configuré", tone: "cobalt" },
  LlmTierConfigured: { label: "Modèle IA configuré", tone: "cobalt" },
  WorkspaceCreated: { label: "Espace créé", tone: "emerald" },
  WorkspacePhaseUpdated: { label: "Phase d'Espace mise à jour", tone: "cobalt" },
  ConnectorConfigured: { label: "Connecteur enregistré", tone: "cobalt" },
  PackRegistered: { label: "Pack activé", tone: "emerald" },
  PackDeactivated: { label: "Pack désactivé", tone: "amber" },
  WorkflowSaved: { label: "Processus enregistré", tone: "cobalt" },
  RunLaunched: { label: "Exécution démarrée", tone: "emerald" },
  OntologyConceptCreated: { label: "Terme métier créé", tone: "cobalt" },
  AdminConnectionTested: { label: "Test de connexion administrateur", tone: "cobalt" },
  StepCompleted: { label: "Étape de processus exécutée", tone: "emerald" },
  GateEvaluated: { label: "Évaluation de validation", tone: "emerald" },
  ArtifactProduced: { label: "Livrable produit", tone: "cobalt" },
  RunTerminated: { label: "Fin d'exécution de processus", tone: "emerald" },
  BudgetCircuitTripped: { label: "Coupe-circuit budgétaire", tone: "amber" },
  BudgetOverrideApproved: { label: "Dérogation budgétaire approuvée", tone: "emerald" },
  RemoteUsageAnomalyCapped: { label: "Télémétrie externe plafonnée", tone: "amber" },
  ConnectorCircuitTripped: { label: "Coupe-circuit de connecteur", tone: "amber" },
  ORG_UNIT_CREATED: { label: "Unité d'organisation créée", tone: "cobalt" },
  ORG_UNIT_UPDATED: { label: "Unité d'organisation mise à jour", tone: "cobalt" },
  ORG_UNIT_DELETED: { label: "Unité d'organisation supprimée", tone: "amber" },
  IAM_ACCOUNT_CREATED: { label: "Compte IAM créé", tone: "emerald" },
  IAM_ACCOUNT_UPDATED: { label: "Compte IAM mis à jour", tone: "cobalt" },
  IAM_ACCOUNT_DELETED: { label: "Compte IAM supprimé", tone: "amber" },
  IAM_ACCOUNT_INVITED: { label: "Collaborateur invité", tone: "emerald" },
};

export const EVENT_TYPE_EN_LABELS: Record<string, { label: string; tone: StatusBadgeTone }> = {
  PlatformAdminInitialized: { label: "Administrator initialized", tone: "emerald" },
  OrgUnitCreated: { label: "Organization unit created", tone: "cobalt" },
  OrgUnitDeleted: { label: "Organization unit deleted", tone: "amber" },
  PermissionGranted: { label: "Permission granted", tone: "emerald" },
  PermissionRevoked: { label: "Permission revoked", tone: "amber" },
  RbacGrantCreated: { label: "Permission granted", tone: "emerald" },
  SettingsChanged: { label: "Setting configured", tone: "cobalt" },
  LlmTierConfigured: { label: "AI model configured", tone: "cobalt" },
  WorkspaceCreated: { label: "Workspace created", tone: "emerald" },
  WorkspacePhaseUpdated: { label: "Workspace phase updated", tone: "cobalt" },
  ConnectorConfigured: { label: "Connector registered", tone: "cobalt" },
  PackRegistered: { label: "Pack enabled", tone: "emerald" },
  PackDeactivated: { label: "Pack disabled", tone: "amber" },
  WorkflowSaved: { label: "Process saved", tone: "cobalt" },
  RunLaunched: { label: "Run started", tone: "emerald" },
  OntologyConceptCreated: { label: "Glossary term created", tone: "cobalt" },
  AdminConnectionTested: { label: "Administrator connection test", tone: "cobalt" },
  StepCompleted: { label: "Process step executed", tone: "emerald" },
  GateEvaluated: { label: "Gate evaluated", tone: "emerald" },
  ArtifactProduced: { label: "Artifact produced", tone: "cobalt" },
  RunTerminated: { label: "Process run completed", tone: "emerald" },
  BudgetCircuitTripped: { label: "Budget circuit tripped", tone: "amber" },
  BudgetOverrideApproved: { label: "Budget override approved", tone: "emerald" },
  RemoteUsageAnomalyCapped: { label: "External usage capped", tone: "amber" },
  ConnectorCircuitTripped: { label: "Connector circuit tripped", tone: "amber" },
  ORG_UNIT_CREATED: { label: "Organization unit created", tone: "cobalt" },
  ORG_UNIT_UPDATED: { label: "Organization unit updated", tone: "cobalt" },
  ORG_UNIT_DELETED: { label: "Organization unit deleted", tone: "amber" },
  IAM_ACCOUNT_CREATED: { label: "IAM account created", tone: "emerald" },
  IAM_ACCOUNT_UPDATED: { label: "IAM account updated", tone: "cobalt" },
  IAM_ACCOUNT_DELETED: { label: "IAM account deleted", tone: "amber" },
  IAM_ACCOUNT_INVITED: { label: "Collaborator invited", tone: "emerald" },
};

export function formatActivityTimestamp(timestampIso: string, isFr: boolean): string {
  return formatShortDateTime(timestampIso, isFr ? "fr" : "en");
}

export interface ScopeSourceOrgUnit {
  readonly id: string;
  readonly name: string;
  readonly slug: string;
  readonly level: "BU" | "TEAM";
  readonly parentId?: string;
}

export interface ScopeSourceWorkspace {
  readonly workspaceId: string;
  readonly name: string;
  readonly ownerOrgUnitId?: string;
  readonly visibilityMode?: string;
}

function collectDescendantUnits(
  rootId: string,
  orgUnits: readonly ScopeSourceOrgUnit[],
): readonly ScopeSourceOrgUnit[] {
  const out: ScopeSourceOrgUnit[] = [];
  const queue = [rootId];
  const seen = new Set<string>([rootId]);
  while (queue.length > 0) {
    const curr = queue.shift()!;
    for (const u of orgUnits) {
      if (u.parentId === curr && !seen.has(u.id)) {
        seen.add(u.id);
        out.push(u);
        queue.push(u.id);
      }
    }
  }
  return out;
}

export function buildActivityScopeOptions(
  orgUnits: readonly ScopeSourceOrgUnit[],
  workspaces: readonly ScopeSourceWorkspace[],
  labels: {
    entirePlatform: string;
    divisionPrefix: string;
    teamPrefix: string;
    privateSpacePrefix: string;
    spacePrefix: string;
  },
  options?: {
    readonly includeGlobal?: boolean;
  },
): UiActivityScopeFilterOption[] {
  const includeGlobal = options?.includeGlobal ?? true;
  const globalEntries: UiActivityScopeFilterOption[] = includeGlobal
    ? [
        {
          id: "scope-global",
          label: labels.entirePlatform,
          scopePath: "GLOBAL",
          level: "GLOBAL",
          childScopeIds: [
            ...orgUnits.map((u) => u.id),
            ...workspaces.map((w) => w.workspaceId),
          ],
          childScopePaths: [
            "GLOBAL",
            labels.entirePlatform,
            ...orgUnits.flatMap((u) => [u.slug, u.name]),
            ...workspaces.map((w) => w.name),
          ],
        },
      ]
    : [];

  return [
    ...globalEntries,
    ...orgUnits.map((u): UiActivityScopeFilterOption => {
      const childUnits = collectDescendantUnits(u.id, orgUnits);
      const childTeamIds = new Set([u.id, ...childUnits.map((c) => c.id)]);
      const childWorkspaces = workspaces.filter(
        (w) => w.ownerOrgUnitId && childTeamIds.has(w.ownerOrgUnitId),
      );
      const prefix = u.level === "BU" ? labels.divisionPrefix : labels.teamPrefix;
      return {
        id: u.id,
        label: `${prefix}${u.name}`,
        scopePath: u.slug,
        level: u.level,
        childScopeIds: [
          ...childUnits.map((c) => c.id),
          ...childWorkspaces.map((w) => w.workspaceId),
        ],
        childScopePaths: [
          u.slug,
          u.name,
          `${prefix}${u.name}`,
          ...childUnits.flatMap((c) => [c.slug, c.name]),
          ...childWorkspaces.flatMap((w) => [w.workspaceId, w.name]),
        ],
      };
    }),
    ...workspaces.map((ws): UiActivityScopeFilterOption => {
      const prefix =
        ws.visibilityMode === "PRIVATE_USER"
          ? labels.privateSpacePrefix
          : labels.spacePrefix;
      return {
        id: ws.workspaceId,
        label: `${prefix}${ws.name}`,
        scopePath: ws.name,
        level: "WORKSPACE",
        childScopeIds: [],
        childScopePaths: [ws.workspaceId, ws.name, `${prefix}${ws.name}`],
      };
    }),
  ];
}
