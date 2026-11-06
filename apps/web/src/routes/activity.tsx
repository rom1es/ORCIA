import {
  ActivityLogExplorerView,
  type ActivityLogExplorerLabels,
  type StatusBadgeTone,
  type UiActivityLogEventItem,
  type UiActivityScopeFilterOption,
} from "@orcia/ui";
import { createRoute } from "@tanstack/react-router";
import React from "react";
import {
  cleanAuditSummaryJargon,
  formatHumanReadableScopePath,
  usePlatformSetup,
} from "../components/platformSetupStore";
import { useShellNavigation } from "../components/ShellContainer";
import { useI18n } from "../i18n";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";

const EVENT_TYPE_FR_LABELS: Record<string, { label: string; tone: StatusBadgeTone }> = {
  PlatformAdminInitialized: { label: "Administrateur initialisé", tone: "emerald" },
  OrgUnitCreated: { label: "Unité d'organisation créée", tone: "cobalt" },
  OrgUnitDeleted: { label: "Unité d'organisation supprimée", tone: "amber" },
  PermissionGranted: { label: "Habilitation attribuée", tone: "emerald" },
  PermissionRevoked: { label: "Habilitation révoquée", tone: "amber" },
  RbacGrantCreated: { label: "Habilitation attribuée", tone: "emerald" },
  SettingsChanged: { label: "Modèle IA configuré", tone: "cobalt" },
  LlmTierConfigured: { label: "Modèle IA configuré", tone: "cobalt" },
  WorkspaceCreated: { label: "Espace créé", tone: "emerald" },
  WorkspacePhaseUpdated: { label: "Phase d'Espace mise à jour", tone: "cobalt" },
  ConnectorConfigured: { label: "Connecteur enregistré", tone: "cobalt" },
  PackRegistered: { label: "Pack activé", tone: "emerald" },
  PackDeactivated: { label: "Pack désactivé", tone: "amber" },
  WorkflowSaved: { label: "Processus enregistré", tone: "cobalt" },
  RunLaunched: { label: "Exécution démarrée", tone: "emerald" },
  OntologyConceptCreated: { label: "Terme métier créé", tone: "cobalt" },
};

const EVENT_TYPE_EN_LABELS: Record<string, { label: string; tone: StatusBadgeTone }> = {
  PlatformAdminInitialized: { label: "Administrator initialized", tone: "emerald" },
  OrgUnitCreated: { label: "Organization unit created", tone: "cobalt" },
  OrgUnitDeleted: { label: "Organization unit deleted", tone: "amber" },
  PermissionGranted: { label: "Permission granted", tone: "emerald" },
  PermissionRevoked: { label: "Permission revoked", tone: "amber" },
  RbacGrantCreated: { label: "Permission granted", tone: "emerald" },
  SettingsChanged: { label: "AI model configured", tone: "cobalt" },
  LlmTierConfigured: { label: "AI model configured", tone: "cobalt" },
  WorkspaceCreated: { label: "Workspace created", tone: "emerald" },
  WorkspacePhaseUpdated: { label: "Workspace phase updated", tone: "cobalt" },
  ConnectorConfigured: { label: "Connector registered", tone: "cobalt" },
  PackRegistered: { label: "Pack enabled", tone: "emerald" },
  PackDeactivated: { label: "Pack disabled", tone: "amber" },
  WorkflowSaved: { label: "Process saved", tone: "cobalt" },
  RunLaunched: { label: "Run started", tone: "emerald" },
  OntologyConceptCreated: { label: "Glossary term created", tone: "cobalt" },
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

export function ActivityLogRouteView(): React.ReactElement {
  const { locale } = useI18n();
  const isFr = locale === "fr";
  const { activeScopeId, openHelpSection } = useShellNavigation();
  const { platformAdmin, orgUnits, workspaces, scopes, auditEvents } = usePlatformSetup();

  const connectedUserName =
    platformAdmin?.displayName ??
    (isFr ? "Administrateur de la plateforme" : "Platform Administrator");

  const scopeOptions: UiActivityScopeFilterOption[] = [
    {
      id: "scope-global",
      label: isFr ? "Plateforme entière" : "Entire Platform",
      scopePath: "GLOBAL",
      level: "GLOBAL",
      childScopeIds: [
        ...orgUnits.map((u) => u.id),
        ...workspaces.map((w) => w.workspaceId),
      ],
      childScopePaths: [
        "GLOBAL",
        "Plateforme entière",
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
      const prefix = u.level === "BU" ? (isFr ? "Direction · " : "Division · ") : (isFr ? "Équipe · " : "Team · ");
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
          ? isFr
            ? "Espace privé · "
            : "Private space · "
          : isFr
            ? "Espace · "
            : "Space · ";
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

  const activeScopeNode = scopes.find((s) => s.id === activeScopeId);
  const activeObservationOption = scopeOptions.find((o) => o.id === activeScopeId);
  const activeObservationScopeLabel =
    activeObservationOption?.label ??
    (activeScopeNode?.level === "GLOBAL"
      ? isFr
        ? "Plateforme entière"
        : "Entire Platform"
      : (activeScopeNode?.name ?? (isFr ? "Plateforme entière" : "Entire Platform")));

  const mappedEvents: UiActivityLogEventItem[] = auditEvents.map((ev) => {
    const typeMap = isFr ? EVENT_TYPE_FR_LABELS : EVENT_TYPE_EN_LABELS;
    const resolvedType = typeMap[ev.eventType] ?? {
      label: isFr ? "Action enregistrée" : "Recorded action",
      tone: "cobalt" as const,
    };
    const rawScopePath = ev.scopePath ?? "GLOBAL";
    const resolvedScopeLabel =
      ev.scopeLabel && ev.scopeLabel !== "GLOBAL"
        ? ev.scopeLabel
        : formatHumanReadableScopePath(rawScopePath);

    return {
      id: ev.id,
      timestampIso: ev.timestampIso,
      formattedTimestamp: formatActivityTimestamp(ev.timestampIso, isFr),
      eventType: ev.eventType,
      eventTypeLabel: resolvedType.label,
      badgeTone: resolvedType.tone,
      summary: cleanAuditSummaryJargon(ev.summary),
      actorName: ev.actorName?.trim() || connectedUserName,
      actorEmail: ev.actorEmail ?? platformAdmin?.email,
      scopeId: ev.scopeId,
      scopePath: rawScopePath,
      scopeLabel: resolvedScopeLabel,
    };
  });

  const labels: ActivityLogExplorerLabels = isFr
    ? {
        pageTitle: "Journal d'Activité",
        pageSubtitle:
          "Consultez l'historique horodaté des actions réalisées sur la plateforme, filtré par défaut sur votre niveau d'observation actif.",
        infoButtonLabel:
          "Comprendre le journal d'activité, ses filtres et le filtrage sur votre niveau d'observation",
        observationScopeBannerPrefix: "Filtré sur votre niveau d'observation :",
        resetToObservationScopeCta: "Revenir à mon niveau d'observation",
        scopeFilterLabel: "Périmètre observé",
        allScopesOptionLabel: "Tous les périmètres",
        userFilterLabel: "Utilisateur (Auteur)",
        allUsersOptionLabel: "Tous les utilisateurs",
        userSearchPlaceholder: "Filtrer par nom d'utilisateur...",
        maxLimitFilterLabel: "Nombre maximum d'événements",
        limit50Label: "50 derniers",
        limit100Label: "100 derniers",
        limit200Label: "200 derniers",
        limit500Label: "500 derniers",
        timeWindowFilterLabel: "Fenêtre temporelle",
        windowAllLabel: "Toute la période",
        window1hLabel: "Dernière heure",
        window24hLabel: "Dernières 24 heures",
        window7dLabel: "7 derniers jours",
        window30dLabel: "30 derniers jours",
        customDateFromLabel: "Du :",
        customDateToLabel: "Au :",
        resultsCounterPrefix: "Événements affichés :",
        emptyStateMessage: "Aucun événement enregistré sur ce périmètre.",
        actorPrefix: "Auteur",
        scopePrefix: "Périmètre",
        timestampPrefix: "Horodatage",
      }
    : {
        pageTitle: "Activity Log",
        pageSubtitle:
          "Review the timestamped history of actions performed across the platform, filtered by default to your active observation scope.",
        infoButtonLabel:
          "Understand the activity log, its filters, and observation scope filtering",
        observationScopeBannerPrefix: "Filtered to your observation scope:",
        resetToObservationScopeCta: "Reset to my observation scope",
        scopeFilterLabel: "Observed scope",
        allScopesOptionLabel: "All scopes",
        userFilterLabel: "User (Author)",
        allUsersOptionLabel: "All users",
        userSearchPlaceholder: "Filter by user name...",
        maxLimitFilterLabel: "Maximum recent events",
        limit50Label: "Last 50",
        limit100Label: "Last 100",
        limit200Label: "Last 200",
        limit500Label: "Last 500",
        timeWindowFilterLabel: "Time window",
        windowAllLabel: "All time",
        window1hLabel: "Last hour",
        window24hLabel: "Last 24 hours",
        window7dLabel: "Last 7 days",
        window30dLabel: "Last 30 days",
        customDateFromLabel: "From:",
        customDateToLabel: "To:",
        resultsCounterPrefix: "Displayed events:",
        emptyStateMessage: "No activity event recorded on this scope.",
        actorPrefix: "Author",
        scopePrefix: "Scope",
        timestampPrefix: "Timestamp",
      };

  return (
    <ActivityLogExplorerView
      events={mappedEvents}
      scopeOptions={scopeOptions}
      activeObservationScopeId={activeScopeId}
      activeObservationScopeLabel={activeObservationScopeLabel}
      connectedUserName={connectedUserName}
      labels={labels}
      onOpenHelpSection={openHelpSection}
    />
  );
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/activity",
  validateSearch: validateOrciaRouteSearch,
  component: ActivityLogRouteView,
});
