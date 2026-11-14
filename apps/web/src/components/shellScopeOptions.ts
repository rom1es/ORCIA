import {
  getOrciaIconGlyph,
  type ControlCenterRunItem,
  type ControlCenterWorkspaceGovItem,
  type EightFixedMenuKey,
  type UiNotificationCenterItem,
  type UiScopeNode,
} from "@orcia/ui";
import type {
  ConfiguredLlmTierMapping,
  ConfiguredOrgUnit,
  ConfiguredPlatformAdmin,
} from "./platformSetupStore";
import type { WorkspaceSseClaimEvent } from "./useWorkspaceEventsSse";

export interface WorkspaceSwitcherOptionItem {
  readonly id: string;
  readonly label: string;
  readonly groupLabel: string;
}

export function buildWorkspaceSwitcherOptions(params: {
  readonly isFr: boolean;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly scopes: readonly UiScopeNode[];
}): readonly WorkspaceSwitcherOptionItem[] {
  const { isFr, orgUnits, workspaces, scopes } = params;
  const privateWorkspaces = workspaces.filter((ws) => ws.visibilityMode === "PRIVATE_USER");
  const teamUnits = orgUnits.filter((u) => u.level === "TEAM");
  const buUnits = orgUnits.filter((u) => u.level === "BU");
  const sharedOrConfidentialWorkspaces = workspaces.filter(
    (ws) => ws.visibilityMode !== "PRIVATE_USER",
  );

  const resolveOwnerName = (ws: ControlCenterWorkspaceGovItem): string => {
    if (ws.ownerOrgUnitId) {
      const matched = orgUnits.find(
        (u) => u.id === ws.ownerOrgUnitId || u.slug === ws.ownerOrgUnitId,
      );
      if (matched) {
        return matched.name;
      }
    }
    return ws.ownerOrgUnitName ?? "";
  };

  const groupPrivateLabel = isFr
    ? `${getOrciaIconGlyph("lock")} Mes Espaces Privés`
    : `${getOrciaIconGlyph("lock")} My Private Spaces`;
  const groupTeamUnitLabel = isFr
    ? `${getOrciaIconGlyph("team")} Mes Équipes & Espaces · Équipe`
    : `${getOrciaIconGlyph("team")} My Teams & Spaces · Team`;
  const groupSharedWorkspaceLabel = isFr
    ? `📦 Espace · ${getOrciaIconGlyph("team")} Mes Équipes & Espaces`
    : `📦 Workspace · ${getOrciaIconGlyph("team")} My Teams & Spaces`;
  const groupSupervisionLabel = isFr
    ? `${getOrciaIconGlyph("organizationBu")} Supervision Organisation`
    : `${getOrciaIconGlyph("organizationBu")} Organization Supervision`;

  return [
    ...privateWorkspaces.map((ws) => {
      const ownerName = resolveOwnerName(ws);
      const prefix = isFr ? "🔒 Espace · " : "🔒 Workspace · ";
      return {
        id: ws.workspaceId,
        label: ownerName ? `${prefix}${ws.name} · ${ownerName}` : `${prefix}${ws.name}`,
        groupLabel: groupPrivateLabel,
      };
    }),
    ...teamUnits.map((team) => ({
      id: team.id,
      label: isFr
        ? `${getOrciaIconGlyph("team")} Équipe · ${team.name}`
        : `${getOrciaIconGlyph("team")} Team · ${team.name}`,
      groupLabel: groupTeamUnitLabel,
    })),
    ...sharedOrConfidentialWorkspaces.map((ws) => {
      const ownerName = resolveOwnerName(ws);
      const prefix = isFr ? "📦 Espace · " : "📦 Workspace · ";
      return {
        id: ws.workspaceId,
        label: ownerName ? `${prefix}${ws.name} · ${ownerName}` : `${prefix}${ws.name}`,
        groupLabel: groupSharedWorkspaceLabel,
      };
    }),
    ...buUnits.map((bu) => ({
      id: bu.id,
      label: isFr
        ? `${getOrciaIconGlyph("organizationBu")} Direction (BU) · ${bu.name}`
        : `${getOrciaIconGlyph("organizationBu")} Division (BU) · ${bu.name}`,
      groupLabel: groupSupervisionLabel,
    })),
    ...scopes
      .filter((s) => s.level === "GLOBAL")
      .map((s) => ({
        id: s.id,
        label: s.name,
        groupLabel: groupSupervisionLabel,
      })),
  ];
}

export function buildShellDisabledMenuKeys(params: {
  readonly isFr: boolean;
  readonly llmTiers: readonly ConfiguredLlmTierMapping[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
}): Partial<Record<EightFixedMenuKey, string>> {
  const { isFr, llmTiers, workspaces } = params;
  return {
    ...(llmTiers.length === 0
      ? {
          assistant: isFr
            ? "Configurez au moins un modèle IA et rattachez une Équipe de facturation dans Configuration pour activer Mon Assistant."
            : "Configure at least one AI model and attach a billing Team in Configuration to enable My Assistant.",
          agents: isFr
            ? "Configurez un modèle IA ou activez un Pack et rattachez une Équipe de facturation dans Configuration pour déverrouiller Mes Agents."
            : "Configure an AI model or enable a Pack and attach a billing Team in Configuration to unlock My Agents.",
        }
      : {}),
    ...(workspaces.length === 0 || llmTiers.length === 0
      ? {
          processes: isFr
            ? "Créez un Espace de Travail rattaché à une Équipe de facturation et configurez un modèle IA pour activer Mes Processus."
            : "Create a Workspace attached to a billing Team and configure an AI model to enable My Processes.",
        }
      : {}),
    ...(workspaces.length === 0 && llmTiers.length === 0
      ? {
          finops: isFr
            ? "Configurez un modèle IA ou créez un Espace de Travail rattaché à une Équipe pour consulter le suivi des coûts."
            : "Configure an AI model or create a Workspace attached to a Team to view cost tracking.",
        }
      : {}),
  };
}

export function buildShellNotificationItems(params: {
  readonly isFr: boolean;
  readonly platformAdmin: ConfiguredPlatformAdmin | null;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly llmTiers: readonly ConfiguredLlmTierMapping[];
  readonly runs: readonly ControlCenterRunItem[];
  readonly lastClaimEvent: WorkspaceSseClaimEvent | null;
}): readonly UiNotificationCenterItem[] {
  const { isFr, platformAdmin, orgUnits, workspaces, llmTiers, runs, lastClaimEvent } = params;
  const teamUnits = orgUnits.filter((u) => u.level === "TEAM");
  const memberTeamIds = platformAdmin?.memberTeamIds ?? [];
  const hasBillingTeam =
    memberTeamIds.length > 0 || teamUnits.length > 0 || workspaces.length > 0;

  return [
    ...(llmTiers.length === 0
      ? [
          {
            id: "setup-llm-missing",
            kind: "SETUP_PREREQUISITE" as const,
            badgeLabel: isFr ? "Prérequis requis" : "Prerequisite required",
            title: isFr
              ? "Aucun modèle IA configuré (menus Mon Assistant & Mes Agents verrouillés)"
              : "No AI model configured (My Assistant & My Agents menus locked)",
            description: isFr
              ? "Enregistrez au moins un fournisseur et un modèle IA dans Configuration pour déverrouiller Mon Assistant, Mes Agents et Mes Processus."
              : "Register at least one AI provider and model in Configuration to unlock My Assistant, My Agents, and My Processes.",
            targetRoute: "/settings",
            ctaLabel: isFr ? "Configurer →" : "Configure →",
          },
        ]
      : []),
    ...(!hasBillingTeam
      ? [
          {
            id: "setup-billing-team-missing",
            kind: "SETUP_PREREQUISITE" as const,
            badgeLabel: isFr ? "Équipe de facturation" : "Billing Team",
            title: isFr
              ? "Aucune Équipe de facturation rattachée (appels IA verrouillés)"
              : "No billing Team attached (AI calls locked)",
            description: isFr
              ? "Tout appel IA doit être rattaché à une Équipe de facturation et un Espace de Travail. Créez une Équipe dans Configuration › Organisation et rattachez-y votre compte."
              : "Every AI call must be attached to a billing Team and a Workspace. Create a Team in Configuration › Organization and attach your account.",
            targetRoute: "/settings",
            ctaLabel: isFr ? "Créer une Équipe →" : "Create a Team →",
          },
        ]
      : []),
    ...(orgUnits.length === 0
      ? [
          {
            id: "setup-org-missing",
            kind: "SETUP_PREREQUISITE" as const,
            badgeLabel: isFr ? "Organisation" : "Organization",
            title: isFr
              ? "Structure d'organisation (Directions / BU & Équipes) à définir"
              : "Organization structure (Divisions / BUs & Teams) to define",
            description: isFr
              ? "Créez au moins une Direction (BU) ou une Équipe dans Configuration pour déverrouiller l'attribution des règles d'habilitation."
              : "Create at least one Division (BU) or Team in Configuration to unlock permission rule grants.",
            targetRoute: "/settings",
            ctaLabel: isFr ? "Structurer →" : "Structure →",
          },
        ]
      : []),
    ...(workspaces.length === 0
      ? [
          {
            id: "setup-workspace-missing",
            kind: "SETUP_PREREQUISITE" as const,
            badgeLabel: isFr ? "Espace requis" : "Workspace required",
            title: isFr
              ? "Aucun Espace de travail créé (menu Mes Processus verrouillé)"
              : "No Workspace created (My Processes menu locked)",
            description: isFr
              ? "Créez votre premier Espace de travail (collectif ou privé rattaché à une Équipe de facturation) dans 📦 Mes Espaces pour rattacher vos sources documentaires et lancer des processus."
              : "Create your first Workspace (team or private attached to a billing Team) in 📦 My Spaces to attach document sources and launch processes.",
            targetRoute: "/workspaces",
            ctaLabel: isFr ? "Créer un Espace →" : "Create Workspace →",
          },
        ]
      : []),
    ...runs.map((run) => ({
      id: `run-decision-${run.runId}`,
      kind: "DECISION_WAITING" as const,
      badgeLabel: isFr ? "Décision attendue" : "Decision pending",
      title: run.title,
      description: `${run.workspaceName} • ${run.currentStepKey} — ${run.blackboardSummary}`,
      targetRoute: "/cockpit",
      ctaLabel: isFr ? "Ouvrir →" : "Open →",
    })),
    ...(lastClaimEvent
      ? [
          {
            id: `sse-claim-${lastClaimEvent.eventId}`,
            kind: "DECISION_WAITING" as const,
            badgeLabel: isFr ? "Présence temps réel" : "Live presence",
            title:
              lastClaimEvent.eventName === "task.claim.locked"
                ? isFr
                  ? `Étape prise en charge (${lastClaimEvent.stepExecutionId})`
                  : `Step claimed (${lastClaimEvent.stepExecutionId})`
                : isFr
                  ? `Étape libérée (${lastClaimEvent.stepExecutionId})`
                  : `Step released (${lastClaimEvent.stepExecutionId})`,
            description: `${lastClaimEvent.workspaceId} • ${lastClaimEvent.dispatchLatencyMs} ms`,
            targetRoute: "/cockpit",
            ctaLabel: isFr ? "Voir →" : "View →",
          },
        ]
      : []),
  ];
}
