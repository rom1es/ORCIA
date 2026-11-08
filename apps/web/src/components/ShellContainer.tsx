import { createOrciaApiClient } from "@orcia/api-client";
import {
  ContextualHelpColumnAndCenter,
  DEFAULT_RGAA_MODAL_LABELS_EN,
  DEFAULT_RGAA_MODAL_LABELS_FR,
  DisabledButtonAlertIndicator,
  FourZoneDirectionCShell,
  getOrciaIconGlyph,
  OrciaIcon,
  RgaaUnsavedChangesAlert,
  TopHeaderSearchCommand,
  UserAccountDropdownAndSettingsModal,
  computeDefaultHelpColumnOpen,
  handleRgaaSubmitKeyDown,
  useUnsavedChangesDialogGuard,
  type EightFixedMenuKey,
  type TopSearchFamilyKey,
  type TopSearchHitItem,
  type UiHumanProfileBadge,
  type UiModuleKey,
  type UiNotificationCenterItem,
} from "@orcia/ui";
import React, { createContext, useContext, useEffect, useState } from "react";
import { useI18n } from "../i18n";
import { buildContextualHelpArticle } from "./contextualHelpCatalog";
import { useOrciaNavigation } from "./navigationAdapter";
import { PlatformSetupProvider, usePlatformSetup } from "./platformSetupStore";
import {
  DEFAULT_HUMAN_PROFILE,
  DEFAULT_SHELL_MODULES,
  EMPTY_DEFAULT_SCOPES,
  evaluateScopeModuleVisibility,
  mapEightMenuKeyToModule,
  resolveEightMenuKeyFromModule,
  resolveModuleFromPathname,
} from "./shellPresets";

export {
  DEFAULT_HUMAN_PROFILE,
  DEFAULT_SHELL_MODULES,
  EMPTY_DEFAULT_SCOPES,
  evaluateScopeModuleVisibility,
  mapEightMenuKeyToModule,
  resolveEightMenuKeyFromModule,
  resolveModuleFromPathname,
};

export interface ShellNavigationContextValue {
  readonly activeModuleKey: UiModuleKey;
  readonly activeMenuKey: EightFixedMenuKey;
  readonly activeScopeId: string;
  readonly helpColumnOpen: boolean;
  readonly activeHelpSectionId: string | null;
  readonly navigateToRoute: (href: string) => void;
  readonly openHelpSection: (sectionId: string) => void;
}

const ShellNavigationContext = createContext<ShellNavigationContextValue>({
  activeModuleKey: "cockpit",
  activeMenuKey: "cockpit",
  activeScopeId: "scope-global",
  helpColumnOpen: true,
  activeHelpSectionId: null,
  navigateToRoute: () => undefined,
  openHelpSection: () => undefined,
});

export function useShellNavigation(): ShellNavigationContextValue {
  return useContext(ShellNavigationContext);
}

function InnerShellContainer({
  children,
  onNavigate,
}: {
  children: React.ReactNode;
  onNavigate?: (href: string) => void;
}) {
  const { locale, dictionary, toggleLocale } = useI18n();
  const { pathname, navigateTo } = useOrciaNavigation();
  const {
    platformAdmin,
    scopes,
    orgUnits,
    workspaces,
    catalogItems,
    ontologyConcepts,
    llmTiers,
    runs,
    createPlatformAdmin,
  } = usePlatformSetup();
  const [activeScopeId, setActiveScopeId] = useState("scope-global");
  const [selectedModuleOverride, setSelectedModuleOverride] = useState<UiModuleKey | null>(null);
  const [selectedMenuKeyOverride, setSelectedMenuKeyOverride] =
    useState<EightFixedMenuKey | null>(null);
  const [searchModalOpen, setSearchModalOpen] = useState<boolean>(false);
  const [speed2Hits, setSpeed2Hits] = useState<readonly TopSearchHitItem[]>([]);
  const [speed2Loading, setSpeed2Loading] = useState<boolean>(false);
  const [helpColumnOpen, setHelpColumnOpen] = useState<boolean>(() =>
    computeDefaultHelpColumnOpen(1440, runs.length),
  );
  const [activeHelpSectionId, setActiveHelpSectionId] = useState<string | null>(null);

  const runFederatedSpeed2Search = (query: string) => {
    const trimmed = query.trim();
    if (!trimmed) {
      setSpeed2Hits([]);
      setSpeed2Loading(false);
      return;
    }
    setSpeed2Loading(true);
    const localSemanticHit: TopSearchHitItem = {
      itemId: `semantic-${trimmed.toLowerCase().replace(/[^a-z0-9]/g, "-")}`,
      family: "SOURCES_SNIPPETS",
      title: isFr
        ? `Passage pertinent pour « ${trimmed} »`
        : `Relevant passage for "${trimmed}"`,
      snippet: isFr
        ? `Recherche approfondie sur l'espace « ${activeWorkspaceName} »`
        : `Deep search across workspace "${activeWorkspaceName}"`,
      workspaceId: activeScopeId,
      screenRoute: pathname ?? "/cockpit",
      deepLinkUri: pathname ?? "/cockpit",
      speedTier: 2,
      lockedTop: false,
      score: 0.88,
      badge: "✨ Passage proche",
      highlightDurationMs: 2000,
      opensContextualHelpColumn: false,
    };
    const client = createOrciaApiClient({ baseUrl: "" });
    void client
      .searchFederated(trimmed, "GLOBAL", workspaces[0]?.workspaceId ?? null, pathname ?? "/spaces")
      .then((res) => {
        setSpeed2Loading(false);
        const mapped = (res.hits ?? []).map(
          (hit): TopSearchHitItem => ({
            itemId: hit.item_id,
            family: (hit.family as TopSearchFamilyKey) ?? "SOURCES_SNIPPETS",
            title: hit.title,
            snippet: hit.snippet,
            workspaceId: hit.workspace_id,
            screenRoute: hit.screen_route,
            deepLinkUri: hit.deep_link_uri,
            speedTier: 2,
            lockedTop: false,
            score: Number(hit.score ?? 0.85),
            badge: hit.badge ?? "✨ Passage proche",
            highlightDurationMs: Number(hit.highlight_duration_ms ?? 2000),
            opensContextualHelpColumn: Boolean(hit.opens_contextual_help_column),
          }),
        );
        setSpeed2Hits(mapped.length > 0 ? mapped : [localSemanticHit]);
      })
      .catch(() => {
        setSpeed2Loading(false);
        setSpeed2Hits([localSemanticHit]);
      });
  };

  // First-boot Platform Administrator setup modal state (starts 100% empty)
  const [adminFullName, setAdminFullName] = useState<string>("");
  const [adminEmail, setAdminEmail] = useState<string>("");
  const [adminPassword, setAdminPassword] = useState<string>("");
  const [adminModalDismissed, setAdminModalDismissed] = useState<boolean>(false);

  useEffect(() => {
    setSelectedModuleOverride(null);
    setSelectedMenuKeyOverride(null);
  }, [pathname]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchModalOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const activeModuleKey = selectedModuleOverride ?? resolveModuleFromPathname(pathname);
  const selectedScope =
    scopes.find((s) => s.id === activeScopeId) ?? scopes[0] ?? EMPTY_DEFAULT_SCOPES[0]!;

  const effectiveProfile: UiHumanProfileBadge = {
    ...DEFAULT_HUMAN_PROFILE,
    displayName: platformAdmin?.displayName ?? DEFAULT_HUMAN_PROFILE.displayName,
    accessMode: selectedScope.accessMode,
  };

  const safeModuleKey: UiModuleKey = activeModuleKey;

  const activeMenuKey: EightFixedMenuKey =
    selectedMenuKeyOverride ?? resolveEightMenuKeyFromModule(safeModuleKey, pathname);

  const dispatchNavigation = (href: string) => {
    if (onNavigate) {
      onNavigate(href);
    } else {
      navigateTo(href);
    }
  };

  const openHelpSection = (sectionId: string) => {
    setHelpColumnOpen(true);
    setActiveHelpSectionId(sectionId);
  };

  const activeWorkspaceName =
    selectedScope.name ?? workspaces[0]?.name ?? "Plateforme Globale ORCIA";

  const isFr = locale === "fr";
  const privateWorkspaces = workspaces.filter((ws) => ws.visibilityMode === "PRIVATE_USER");
  const teamUnits = orgUnits.filter((u) => u.level === "TEAM");
  const buUnits = orgUnits.filter((u) => u.level === "BU");
  const sharedOrConfidentialWorkspaces = workspaces.filter(
    (ws) => ws.visibilityMode !== "PRIVATE_USER",
  );
  const memberTeamIds = platformAdmin?.memberTeamIds ?? [];
  const hasBillingTeam =
    memberTeamIds.length > 0 || teamUnits.length > 0 || workspaces.length > 0;

  const groupPrivateLabel = isFr
    ? `${getOrciaIconGlyph("lock")} Mes Espaces Privés`
    : `${getOrciaIconGlyph("lock")} My Private Spaces`;
  const groupTeamsLabel = isFr
    ? `${getOrciaIconGlyph("team")} Mes Équipes & Espaces`
    : `${getOrciaIconGlyph("team")} My Teams & Spaces`;
  const groupSupervisionLabel = isFr
    ? `${getOrciaIconGlyph("organizationBu")} Supervision Organisation`
    : `${getOrciaIconGlyph("organizationBu")} Organization Supervision`;

  const workspaceOptions = [
    ...privateWorkspaces.map((ws) => ({
      id: ws.workspaceId,
      label: ws.ownerOrgUnitName ? `${ws.name} · ${ws.ownerOrgUnitName}` : ws.name,
      groupLabel: groupPrivateLabel,
    })),
    ...teamUnits.map((team) => ({
      id: team.id,
      label: team.name,
      groupLabel: groupTeamsLabel,
    })),
    ...sharedOrConfidentialWorkspaces.map((ws) => ({
      id: ws.workspaceId,
      label: ws.ownerOrgUnitName ? `${ws.name} · ${ws.ownerOrgUnitName}` : ws.name,
      groupLabel: groupTeamsLabel,
    })),
    ...buUnits.map((bu) => ({
      id: bu.id,
      label: bu.name,
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

  const disabledMenuKeys: Partial<Record<EightFixedMenuKey, string>> = {
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

  const notificationItems: readonly UiNotificationCenterItem[] = [
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
  ];

  const contextualHelpArticle = buildContextualHelpArticle({
    activeMenuKey,
    pathname,
    locale,
    title: dictionary.fourZoneShell.menuEntries[activeMenuKey],
    defaultSummary: dictionary.modulePages[safeModuleKey].description,
  });

  const isAdminModalOpen = platformAdmin === null && !adminModalDismissed;
  const isAdminModalDirty = Boolean(
    adminFullName.trim() || adminEmail.trim() || adminPassword.trim(),
  );
  const canCreateAdmin = Boolean(adminFullName.trim() && adminEmail.trim());
  const rgaaLabels = isFr ? DEFAULT_RGAA_MODAL_LABELS_FR : DEFAULT_RGAA_MODAL_LABELS_EN;

  const {
    showUnsavedConfirm: showAdminUnsavedConfirm,
    requestClose: requestCloseAdminModal,
    confirmDiscardAndClose: confirmDiscardAdminModal,
    cancelDiscardAndStay: cancelDiscardAdminModal,
    handleDialogKeyDown: handleAdminDialogKeyDown,
  } = useUnsavedChangesDialogGuard({
    isOpen: isAdminModalOpen,
    isDirty: isAdminModalDirty,
    onClose: () => setAdminModalDismissed(true),
    onDiscardUnsavedChanges: () => {
      setAdminFullName("");
      setAdminEmail("");
      setAdminPassword("");
    },
  });

  const submitFirstBootAdmin = () => {
    if (!canCreateAdmin) {
      return;
    }
    createPlatformAdmin({
      displayName: adminFullName.trim(),
      email: adminEmail.trim(),
      password: adminPassword,
    });
  };

  const handleFirstBootAdminSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submitFirstBootAdmin();
  };

  return (
    <ShellNavigationContext.Provider
      value={{
        activeModuleKey: safeModuleKey,
        activeMenuKey,
        activeScopeId: selectedScope.id,
        helpColumnOpen,
        activeHelpSectionId,
        navigateToRoute: dispatchNavigation,
        openHelpSection,
      }}
    >
      <FourZoneDirectionCShell
        activeMenuKey={activeMenuKey}
        activityMenuActive={Boolean(pathname?.startsWith("/activity"))}
        activeWorkspaceName={activeWorkspaceName}
        activeScopeId={selectedScope.id}
        workspaceOptions={workspaceOptions}
        onSelectWorkspace={(scopeId) => setActiveScopeId(scopeId)}
        activePackKey=""
        availablePacks={[]}
        userDisplayName={effectiveProfile.displayName}
        userHatLabel="Administrateur de la plateforme"
        pendingDecisionsTotal={runs.length}
        notifications={notificationItems}
        onSelectNotification={(item) => {
          if (item.targetRoute) {
            dispatchNavigation(item.targetRoute);
          }
        }}
        labels={dictionary.fourZoneShell}
        disabledMenuKeys={disabledMenuKeys}
        helpColumnOpen={helpColumnOpen}
        onHelpColumnOpenChange={setHelpColumnOpen}
        onSelectMenu={(menuKey) => {
          const mapped = mapEightMenuKeyToModule(menuKey);
          setSelectedMenuKeyOverride(menuKey);
          setSelectedModuleOverride(mapped.moduleKey);
          dispatchNavigation(mapped.route);
        }}
        onSelectActivityMenu={(route) => {
          setSelectedMenuKeyOverride("finops");
          setSelectedModuleOverride("finops");
          dispatchNavigation(route);
        }}
        onOpenWorkspaceSwitcher={() => undefined}
        onOpenSearchCommand={() => setSearchModalOpen(true)}
        sidebarSecondarySlot={
          pathname?.startsWith("/help") || pathname?.startsWith("/ontology") ? null : (
            <button
              type="button"
              data-testid="open-orcia-showcase-site-btn"
              onClick={() => {
                setSelectedMenuKeyOverride("help");
                setSelectedModuleOverride("ontology");
                dispatchNavigation("/showcase");
              }}
              className="mt-1 flex items-center gap-2 rounded border px-2.5 py-1.5 text-left text-[11px] font-semibold"
              style={{
                backgroundColor: pathname?.startsWith("/showcase")
                  ? "var(--color-action-primary-subtle)"
                  : "var(--color-bg-elevated)",
                borderColor: "var(--color-border-subtle)",
                color: pathname?.startsWith("/showcase")
                  ? "var(--color-action-primary)"
                  : "var(--color-text-primary)",
                cursor: "pointer",
              }}
            >
              <OrciaIcon name="globe" />
              <span>Documentation</span>
            </button>
          )
        }
        headerUserControl={
          <UserAccountDropdownAndSettingsModal
            userDisplayName={effectiveProfile.displayName}
            userEmail={platformAdmin?.email ?? ""}
            userRole={effectiveProfile.role ?? "PLATFORM_ADMIN"}
            initialLocale={locale}
            labels={dictionary.userAccountAndSettings}
            onPreferencesSync={(patch) => {
              if (patch.locale && patch.locale !== locale) {
                toggleLocale();
              }
            }}
            onNavigateAssistantBehavior={(uri) => dispatchNavigation(uri)}
          />
        }
        helpColumnContent={
          <ContextualHelpColumnAndCenter
            mode="COLUMN_340PX"
            route={pathname ?? "/cockpit"}
            pack="orcia-core"
            redisCacheKey={`help:route:${pathname ?? "/cockpit"}:core:${locale}`}
            mergedLayers={["BASE", "PACK", "WORKSPACE"]}
            article={contextualHelpArticle}
            activeSectionId={activeHelpSectionId}
            rollbackAvailable={true}
            isAdmin={true}
            labels={dictionary.contextualHelpHybrid}
            onAskAssistantOnScreen={() => {
              if (!disabledMenuKeys.assistant) {
                setSelectedMenuKeyOverride("assistant");
                setSelectedModuleOverride("inbox");
                dispatchNavigation("/assistant");
              }
            }}
          />
        }
      >
        {children}
      </FourZoneDirectionCShell>

      {/* Modale d'initialisation au 1er démarrage : Création du compte Administrateur de la plateforme */}
      {isAdminModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="first-boot-admin-modal-title"
          data-testid="first-boot-admin-setup-modal"
          onKeyDown={handleAdminDialogKeyDown}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ backgroundColor: "rgba(15, 23, 42, 0.45)" }}
        >
          <div
            className="w-full max-w-md rounded-xl border p-6 shadow-xl space-y-4"
            style={{
              backgroundColor: "var(--color-bg-surface)",
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-primary)",
            }}
          >
            <div>
              <span
                className="inline-block rounded px-2 py-0.5 text-[11px] font-semibold mb-2"
                style={{
                  backgroundColor: "var(--color-action-primary-subtle)",
                  color: "var(--color-action-primary)",
                }}
              >
                {isFr ? "Première mise en route" : "First-Time Setup"}
              </span>
              <h2 id="first-boot-admin-modal-title" className="text-base font-bold">
                {isFr
                  ? "Création du compte Administrateur de la plateforme"
                  : "Create Platform Administrator Account"}
              </h2>
              <p className="mt-1 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                {isFr
                  ? "Aucun compte administrateur n'est encore enregistré. Créez le premier compte Administrateur pour configurer votre organisation."
                  : "No administrator account is registered yet. Create the first Administrator account to configure your organization."}
              </p>
            </div>

            {showAdminUnsavedConfirm ? (
              <RgaaUnsavedChangesAlert
                testIdPrefix="first-boot-admin"
                labels={rgaaLabels}
                onStay={cancelDiscardAdminModal}
                onDiscard={confirmDiscardAdminModal}
              />
            ) : null}

            <form
              onSubmit={handleFirstBootAdminSubmit}
              autoComplete="off"
              data-lpignore="true"
              data-form-type="other"
              className="space-y-3 text-xs"
            >
              <label className="flex flex-col gap-1">
                <span className="font-medium">
                  {isFr ? "Nom complet" : "Full name"}
                </span>
                <input
                  type="text"
                  autoComplete="off"
                  data-lpignore="true"
                  data-1p-ignore="true"
                  data-bwignore="true"
                  data-form-type="other"
                  data-testid="first-boot-admin-name-input"
                  value={adminFullName}
                  onChange={(e) => setAdminFullName(e.target.value)}
                  placeholder={isFr ? "Ex : Romain" : "e.g. Romain"}
                  className="rounded border px-3 py-1.5"
                  style={{
                    backgroundColor: "var(--color-bg-canvas)",
                    borderColor: "var(--color-border-subtle)",
                  }}
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="font-medium">
                  {isFr ? "Adresse e-mail" : "Email address"}
                </span>
                <input
                  type="email"
                  autoComplete="off"
                  data-lpignore="true"
                  data-1p-ignore="true"
                  data-bwignore="true"
                  data-form-type="other"
                  data-testid="first-boot-admin-email-input"
                  value={adminEmail}
                  onChange={(e) => setAdminEmail(e.target.value)}
                  placeholder={isFr ? "admin@entreprise.fr" : "admin@company.com"}
                  className="rounded border px-3 py-1.5"
                  style={{
                    backgroundColor: "var(--color-bg-canvas)",
                    borderColor: "var(--color-border-subtle)",
                  }}
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="font-medium">
                  {isFr ? "Mot de passe" : "Password"}
                </span>
                <input
                  type="text"
                  spellCheck={false}
                  autoComplete="off"
                  data-lpignore="true"
                  data-1p-ignore="true"
                  data-bwignore="true"
                  data-form-type="other"
                  data-testid="first-boot-admin-password-input"
                  value={adminPassword}
                  onChange={(e) => setAdminPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="rounded border px-3 py-1.5 orcia-masked-secret-input"
                  style={
                    {
                      backgroundColor: "var(--color-bg-canvas)",
                      borderColor: "var(--color-border-subtle)",
                      WebkitTextSecurity: "disc",
                    } as React.CSSProperties
                  }
                />
              </label>

              <div className="flex items-center justify-between gap-2 pt-2 flex-wrap">
                <span
                  data-testid="first-boot-admin-role-badge"
                  className="text-[11px] font-medium"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  {isFr ? "Rôle attribué : Administrateur de la plateforme" : "Assigned role: Platform Administrator"}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    data-testid="first-boot-admin-cancel-btn"
                    onClick={requestCloseAdminModal}
                    className="rounded border px-3 py-1.5 font-medium"
                    style={{
                      backgroundColor: "var(--color-bg-canvas)",
                      borderColor: "var(--color-border-subtle)",
                      color: "var(--color-text-secondary)",
                      cursor: "pointer",
                    }}
                  >
                    {rgaaLabels.cancelCta} (Esc)
                  </button>
                  <button
                    type="submit"
                    data-testid="first-boot-admin-submit-btn"
                    disabled={!canCreateAdmin}
                    title={
                      !canCreateAdmin
                        ? isFr
                          ? "Renseignez le nom complet et l'adresse e-mail pour créer le compte Administrateur."
                          : "Enter full name and email address to create the Administrator account."
                        : undefined
                    }
                    onKeyDown={(e) =>
                      handleRgaaSubmitKeyDown(e, submitFirstBootAdmin, !canCreateAdmin)
                    }
                    className="inline-flex items-center gap-1.5 rounded px-4 py-1.5 font-semibold"
                    style={{
                      backgroundColor: "var(--color-action-primary)",
                      color: "var(--color-bg-surface)",
                      opacity: !canCreateAdmin ? 0.55 : 1,
                      cursor: !canCreateAdmin ? "not-allowed" : "pointer",
                    }}
                  >
                    <span>
                      {isFr ? "Créer le compte Administrateur" : "Create Administrator Account"}
                    </span>
                    <DisabledButtonAlertIndicator
                      disabled={!canCreateAdmin}
                      reason={
                        isFr
                          ? "Renseignez le nom complet et l'adresse e-mail pour créer le compte Administrateur."
                          : "Enter full name and email address to create the Administrator account."
                      }
                      testIdSuffix="first-boot-admin-submit-btn"
                    />
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {searchModalOpen && (
        <div
          data-testid="cmdk-modal-backdrop"
          className="fixed inset-0 z-40 flex items-center justify-center p-4"
          style={{ backgroundColor: "rgba(15, 23, 42, 0.35)" }}
        >
          <TopHeaderSearchCommand
            labels={dictionary.topHeaderSearch}
            speed1Hits={[
              ...workspaces.map((ws): TopSearchHitItem => ({
                itemId: ws.workspaceId,
                family: "FOLDERS_DISCUSSIONS",
                title: ws.name,
                snippet: ws.lifecyclePhase,
                workspaceId: ws.workspaceId,
                screenRoute: "/workspaces",
                deepLinkUri: "/workspaces",
                speedTier: 1,
                lockedTop: true,
                score: 0.99,
                badge: null,
                highlightDurationMs: 2000,
                opensContextualHelpColumn: false,
              })),
              ...catalogItems.map((cat): TopSearchHitItem => ({
                itemId: cat.resourceId,
                family: "PROCESSES_EXECUTIONS",
                title: cat.title,
                snippet: cat.uri,
                workspaceId: activeScopeId,
                screenRoute: "/catalog",
                deepLinkUri: "/catalog",
                speedTier: 1,
                lockedTop: true,
                score: 0.95,
                badge: null,
                highlightDurationMs: 2000,
                opensContextualHelpColumn: false,
              })),
              ...ontologyConcepts.map((c): TopSearchHitItem => ({
                itemId: c.conceptKey,
                family: "ONTOLOGY_GLOSSARY",
                title: c.canonicalTerm,
                snippet: c.definitionText,
                workspaceId: activeScopeId,
                screenRoute: "/workspaces",
                deepLinkUri: "/workspaces",
                speedTier: 1,
                lockedTop: true,
                score: 0.92,
                badge: null,
                highlightDurationMs: 2000,
                opensContextualHelpColumn: false,
              })),
            ]}
            speed2Hits={speed2Hits}
            speed2Loading={speed2Loading}
            onQueryChange={(query) => {
              if (!query.trim()) {
                setSpeed2Hits([]);
                setSpeed2Loading(false);
              }
            }}
            onTriggerSpeed2Now={(query) => runFederatedSpeed2Search(query)}
            onSelectDeepLink={(payload) => {
              setSearchModalOpen(false);
              dispatchNavigation(payload.deepLinkUri);
            }}
            onAskAssistant={() => {
              setSearchModalOpen(false);
              if (!disabledMenuKeys.assistant) {
                setSelectedMenuKeyOverride("assistant");
                setSelectedModuleOverride("inbox");
                dispatchNavigation("/assistant");
              }
            }}
            onClose={() => setSearchModalOpen(false)}
          />
        </div>
      )}
    </ShellNavigationContext.Provider>
  );
}

export function ShellContainer({
  children,
  onNavigate,
}: {
  children: React.ReactNode;
  onNavigate?: (href: string) => void;
}) {
  return (
    <PlatformSetupProvider>
      <InnerShellContainer onNavigate={onNavigate}>{children}</InnerShellContainer>
    </PlatformSetupProvider>
  );
}
