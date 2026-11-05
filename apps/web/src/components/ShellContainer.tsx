import {
  ContextualHelpColumnAndCenter,
  DEFAULT_RGAA_MODAL_LABELS_EN,
  DEFAULT_RGAA_MODAL_LABELS_FR,
  FourZoneDirectionCShell,
  RgaaUnsavedChangesAlert,
  TopHeaderSearchCommand,
  UserAccountDropdownAndSettingsModal,
  computeDefaultHelpColumnOpen,
  handleRgaaSubmitKeyDown,
  useUnsavedChangesDialogGuard,
  type EightFixedMenuKey,
  type TopSearchHitItem,
  type UiHumanProfileBadge,
  type UiModuleKey,
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
  const [helpColumnOpen, setHelpColumnOpen] = useState<boolean>(() =>
    computeDefaultHelpColumnOpen(1440, runs.length),
  );
  const [activeHelpSectionId, setActiveHelpSectionId] = useState<string | null>(null);

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
  const workspaceOptions = scopes.map((s) => ({
    id: s.id,
    label: s.name,
    groupLabel:
      s.level === "GLOBAL"
        ? isFr
          ? "Plateforme Globale"
          : "Global Platform"
        : s.level === "BU"
          ? "BU"
          : isFr
            ? "Espace"
            : "Workspace",
  }));

  const disabledMenuKeys: Partial<Record<EightFixedMenuKey, string>> = {
    ...(llmTiers.length === 0
      ? {
          assistant: isFr
            ? "Configurez au moins un modèle IA dans Configuration pour activer Mon Assistant."
            : "Configure at least one AI model in Configuration to enable My Assistant.",
          agents: isFr
            ? "Configurez un modèle IA ou activez un Pack dans Configuration pour déverrouiller Mes Agents."
            : "Configure an AI model or enable a Pack in Configuration to unlock My Agents.",
        }
      : {}),
    ...(workspaces.length === 0 || llmTiers.length === 0
      ? {
          processes: isFr
            ? "Créez un Espace de Travail et configurez un modèle IA pour activer Mes Processus."
            : "Create a Workspace and configure an AI model to enable My Processes.",
        }
      : {}),
    ...(workspaces.length === 0 && llmTiers.length === 0
      ? {
          finops: isFr
            ? "Configurez un modèle IA ou créez un Espace de Travail pour consulter le suivi des coûts."
            : "Configure an AI model or create a Workspace to view cost tracking.",
        }
      : {}),
  };

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
        activeWorkspaceName={activeWorkspaceName}
        activeScopeId={selectedScope.id}
        workspaceOptions={workspaceOptions}
        onSelectWorkspace={(scopeId) => setActiveScopeId(scopeId)}
        activePackKey=""
        availablePacks={[]}
        userDisplayName={effectiveProfile.displayName}
        userHatLabel="Administrateur de la plateforme"
        pendingDecisionsTotal={runs.length}
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
        onOpenWorkspaceSwitcher={() => undefined}
        onOpenSearchCommand={() => setSearchModalOpen(true)}
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

            <form onSubmit={handleFirstBootAdminSubmit} className="space-y-3 text-xs">
              <label className="flex flex-col gap-1">
                <span className="font-medium">
                  {isFr ? "Nom complet" : "Full name"}
                </span>
                <input
                  type="text"
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
                  type="password"
                  data-testid="first-boot-admin-password-input"
                  value={adminPassword}
                  onChange={(e) => setAdminPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="rounded border px-3 py-1.5"
                  style={{
                    backgroundColor: "var(--color-bg-canvas)",
                    borderColor: "var(--color-border-subtle)",
                  }}
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
                    onKeyDown={(e) =>
                      handleRgaaSubmitKeyDown(e, submitFirstBootAdmin, !canCreateAdmin)
                    }
                    className="rounded px-4 py-1.5 font-semibold"
                    style={{
                      backgroundColor: "var(--color-action-primary)",
                      color: "var(--color-bg-surface)",
                      opacity: !canCreateAdmin ? 0.5 : 1,
                      cursor: !canCreateAdmin ? "not-allowed" : "pointer",
                    }}
                  >
                    {isFr ? "Créer le compte Administrateur" : "Create Administrator Account"}
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
                screenRoute: "/ontology",
                deepLinkUri: "/ontology",
                speedTier: 1,
                lockedTop: true,
                score: 0.92,
                badge: null,
                highlightDurationMs: 2000,
                opensContextualHelpColumn: false,
              })),
            ]}
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
