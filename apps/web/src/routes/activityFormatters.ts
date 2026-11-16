import type { StatusBadgeTone, UiActivityScopeFilterOption } from "@orcia/ui";

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
};

export function formatActivityTimestamp(timestampIso: string, isFr: boolean): string {
  const parsed = new Date(timestampIso);
  if (Number.isNaN(parsed.getTime())) {
    return timestampIso;
  }
  const pad = (n: number) => String(n).padStart(2, "0");
  const day = pad(parsed.getUTCDate());
  const month = pad(parsed.getUTCMonth() + 1);
  const year = parsed.getUTCFullYear();
  const hours = pad(parsed.getUTCHours());
  const minutes = pad(parsed.getUTCMinutes());
  const seconds = pad(parsed.getUTCSeconds());
  return isFr
    ? `${day}/${month}/${year} ${hours}:${minutes}:${seconds}`
    : `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
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
): UiActivityScopeFilterOption[] {
  return [
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
    ...orgUnits.map((u): UiActivityScopeFilterOption => {
      const childUnits = orgUnits.filter((c) => c.parentId === u.id);
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
