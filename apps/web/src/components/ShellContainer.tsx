import {
  ContextualHelpColumnAndCenter,
  DEFAULT_RGAA_MODAL_LABELS_EN,
  DEFAULT_RGAA_MODAL_LABELS_FR,
  FourZoneDirectionCShell,
  RgaaUnsavedChangesAlert,
  TopHeaderSearchCommand,
  UserAccountDropdownAndSettingsModal,
  handleRgaaSubmitKeyDown,
  useUnsavedChangesDialogGuard,
  type EightFixedMenuKey,
  type TopSearchHitItem,
  type UiContextualHelpArticleView,
  type UiHumanProfileBadge,
  type UiModuleKey,
} from "@orcia/ui";
import React, { createContext, useContext, useEffect, useState } from "react";
import { useI18n } from "../i18n";
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
  readonly navigateToRoute: (href: string) => void;
}

const ShellNavigationContext = createContext<ShellNavigationContextValue>({
  activeModuleKey: "cockpit",
  activeMenuKey: "cockpit",
  activeScopeId: "scope-global",
  navigateToRoute: () => undefined,
});

export function useShellNavigation(): ShellNavigationContextValue {
  return useContext(ShellNavigationContext);
}

const DEFAULT_SEARCH_HITS: readonly TopSearchHitItem[] = [
  {
    itemId: "hit-cockpit",
    family: "HELP_ACTIONS",
    title: "Cockpit & Décisions Prioritaires",
    snippet: "Pilotez vos arbitrages Tie-Break, ancrages humains et revues 4 blocs.",
    workspaceId: "scope-global",
    screenRoute: "/cockpit",
    deepLinkUri: "/cockpit",
    speedTier: 1,
    lockedTop: true,
    score: 0.99,
    badge: null,
    highlightDurationMs: 2000,
    opensContextualHelpColumn: false,
  },
  {
    itemId: "hit-assistant",
    family: "FOLDERS_DISCUSSIONS",
    title: "Mon Assistant",
    snippet: "Interrogez vos sources avec citations déterministes [S1] / [G1] / [O1].",
    workspaceId: "scope-global",
    screenRoute: "/assistant",
    deepLinkUri: "/assistant",
    speedTier: 1,
    lockedTop: true,
    score: 0.96,
    badge: null,
    highlightDurationMs: 2000,
    opensContextualHelpColumn: false,
  },
  {
    itemId: "hit-spaces",
    family: "ONTOLOGY_GLOSSARY",
    title: "Mes Espaces",
    snippet: "Gérez vos sources, livrables, dérogations et règles métiers Starlark.",
    workspaceId: "scope-global",
    screenRoute: "/workspaces",
    deepLinkUri: "/workspaces",
    speedTier: 1,
    lockedTop: true,
    score: 0.94,
    badge: null,
    highlightDurationMs: 2000,
    opensContextualHelpColumn: false,
  },
];

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
    llmTiers,
    runs,
    createPlatformAdmin,
  } = usePlatformSetup();
  const [activeScopeId, setActiveScopeId] = useState("scope-global");
  const [selectedModuleOverride, setSelectedModuleOverride] = useState<UiModuleKey | null>(null);
  const [selectedMenuKeyOverride, setSelectedMenuKeyOverride] =
    useState<EightFixedMenuKey | null>(null);
  const [searchModalOpen, setSearchModalOpen] = useState<boolean>(false);

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
            ? "Configurez un modèle IA ou créez un Espace de Travail pour consulter le suivi FinOps."
            : "Configure an AI model or create a Workspace to view FinOps tracking.",
        }
      : {}),
  };

  const isConfigurationScreen =
    activeMenuKey === "configuration" ||
    pathname === "/settings" ||
    pathname === "/configuration";

  const contextualHelpArticle: UiContextualHelpArticleView = isConfigurationScreen
    ? {
        resourceId: `help-${activeMenuKey}`,
        uri: `orcia://packs/core/help/${activeMenuKey}/${locale}`,
        title: dictionary.fourZoneShell.menuEntries[activeMenuKey],
        version: "1.0.0",
        lang: locale,
        layer: "PACK",
        packName: "orcia-core",
        boundRoutes: [pathname ?? "/settings"],
        summaryWhatFor: isFr
          ? "Cet écran structure votre organisation (BU et Espaces), pilote vos règles d'habilitation (les 6 verbes de permissions : create, read, update, delete, execute, grant), vos modèles IA et vos connecteurs."
          : "This screen structures your organization (BUs and Workspaces), governs permission rules (the 6 permission verbs: create, read, update, delete, execute, grant), AI models, and connectors.",
        stepByStepItems: isFr
          ? [
              "1. Créez vos BU (Business Units / Directions), puis créez vos Espaces (Équipes) en les rattachant à leur BU parente. La suppression est protégée contre les orphelins.",
              "2. Dans Habilitations, indiquez Qui ? (Bénéficiaire : Rôle ou Utilisateur, ex: ROLE:Chef1) et Sur quoi ? (Périmètre cible : GLOBAL, BU ou Espace, ex: aqwZSX).",
              "3. Cochez les actions autorisées (ou Tous) et choisissez l'effet (ALLOW, DENY ou INHERITANCE_BLOCK). Utilisez les cases à cocher de la liste pour supprimer une ou plusieurs règles.",
            ]
          : [
              "1. Create your BUs (Business Units), then create your Workspaces (Teams) linked to their parent BU. Deletion is protected against orphans.",
              "2. In Permissions, specify Who? (Beneficiary: Role or User, e.g. ROLE:Chef1) and On what? (Target scope: GLOBAL, BU, or Workspace, e.g. aqwZSX).",
              "3. Check allowed actions (or All) and choose the effect (ALLOW, DENY, or INHERITANCE_BLOCK). Use the list checkboxes to delete one or more rules.",
            ],
        keyTermsItems: isFr
          ? [
              "BU vs Espace (Équipe) : Une BU est une direction ou pôle métier qui regroupe plusieurs Espaces. Un Espace correspond à une équipe ou un périmètre de travail rattaché à une BU.",
              "Protection anti-orphelins : Impossible de supprimer une BU ou un Espace tant que des sous-espaces ou des règles d'habilitation y sont rattachés.",
              "Qui ? (Bénéficiaire) vs Sur quoi ? (Périmètre cible) : Dans « ROLE:Chef1 → aqwZSX », Chef1 est le Bénéficiaire (le rôle ou l'utilisateur qui reçoit le droit) et aqwZSX est le Périmètre cible (la BU, l'Espace ou la ressource sur laquelle s'applique ce droit).",
              "Les 6 verbes d'habilitation (IAM) : create (créer), read (lire/voir les secrets), update (modifier), delete (supprimer), execute (utiliser un agent/modèle/connecteur sans voir ses secrets), grant (déléguer ses droits).",
              "ALLOW (Autoriser) : Accorde explicitement les verbes cochés au bénéficiaire sur le périmètre cible.",
              "DENY (Interdire — prioritaire) : Refuse explicitement les verbes cochés. Un DENY l'emporte toujours sur n'importe quel ALLOW.",
              "INHERITANCE_BLOCK (Bloquer l'héritage parent) : Coupe la transmission automatique des droits hérités des niveaux supérieurs (Plateforme Globale ou BU parente) sur ce périmètre, afin de repartir d'une feuille blanche locale.",
            ]
          : [
              "BU vs Workspace (Team): A BU is a business division grouping multiple Workspaces. A Workspace is a team scope linked to a parent BU.",
              "Orphan protection: A BU or Workspace cannot be deleted while child workspaces or permission rules still depend on it.",
              "Who? (Beneficiary) vs On what? (Target scope): In 'ROLE:Chef1 → aqwZSX', Chef1 is the Beneficiary (the role or user receiving the right) and aqwZSX is the Target scope (the BU, Workspace, or resource).",
              "The 6 permission verbs (IAM): create, read (view config/secrets), update, delete, execute (run an agent/model/connector without reading secrets), grant (delegate rights).",
              "ALLOW: Explicitly grants the checked verbs to the beneficiary on the target scope.",
              "DENY (Priority override): Explicitly denies the checked verbs. DENY always overrides any ALLOW.",
              "INHERITANCE_BLOCK (Block parent inheritance): Stops automatic inheritance of permissions from parent levels (Global Platform or parent BU) on this scope, starting from a clean local slate.",
            ],
        faqItems: isFr
          ? [
              "Pourquoi ne puis-je pas supprimer une BU ou un Espace ? → Pour éviter de rendre orphelins des Espaces enfants ou des règles d'habilitation qui y font référence. Supprimez ou détachez d'abord les éléments dépendants.",
              "Quelle est la différence entre execute et read ? → execute permet d'utiliser un modèle IA ou connecteur dans un processus sans pouvoir lire sa clé secrète (read).",
              "Quand utiliser INHERITANCE_BLOCK ? → Lorsqu'un Espace confidentiel ne doit plus hériter des accès larges accordés au niveau de sa BU parente.",
            ]
          : [
              "Why can't I delete a BU or Workspace? → To prevent orphaning child Workspaces or permission rules that reference it. Remove dependent items first.",
              "What is the difference between execute and read? → execute lets a user run an AI model or connector without viewing its secret key (read).",
              "When should I use INHERITANCE_BLOCK? → When a confidential Workspace must stop inheriting broad permissions granted at its parent BU level.",
            ],
        casKey: "cas/help_contextual_v1",
        sha256: "sha256_contextual_help_v1",
        previousVersion: "0.9.0",
      }
    : {
        resourceId: `help-${activeMenuKey}`,
        uri: `orcia://packs/core/help/${activeMenuKey}/${locale}`,
        title: dictionary.fourZoneShell.menuEntries[activeMenuKey],
        version: "1.0.0",
        lang: locale,
        layer: "PACK",
        packName: "orcia-core",
        boundRoutes: [pathname ?? "/cockpit"],
        summaryWhatFor: dictionary.modulePages[safeModuleKey].description,
        stepByStepItems: [
          "1. Sélectionnez votre Espace actif dans la barre supérieure.",
          "2. Utilisez la recherche fédérée ⌘K ou Mon Assistant pour interroger vos sources.",
          "3. Validez les décisions en attente ou lancez un processus gouverné.",
        ],
        keyTermsItems: ["Ancrage Humain Violet", "Action Staged", "Chaîne Causale ADN"],
        faqItems: ["Comment personnaliser Mon Assistant ? → Cliquez sur ⚙ Réglages de l'assistant."],
        casKey: "cas/help_contextual_v1",
        sha256: "sha256_contextual_help_v1",
        previousVersion: "0.9.0",
      };

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
        navigateToRoute: dispatchNavigation,
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

      {/* Modale d'amorçage au 1er démarrage : Création du compte Administrateur de la plateforme */}
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
                {isFr ? "Premier démarrage · Jour 0" : "First Boot · Day 0"}
              </span>
              <h2 id="first-boot-admin-modal-title" className="text-base font-bold">
                {isFr
                  ? "Création du compte Administrateur de la plateforme"
                  : "Create Platform Administrator Account"}
              </h2>
              <p className="mt-1 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                {isFr
                  ? "Aucun compte administrateur n'est encore configuré. Initialisez le premier compte Administrateur de la plateforme pour démarrer la configuration."
                  : "No administrator account is configured yet. Initialize the first Platform Administrator account to start configuration."}
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
            speed1Hits={DEFAULT_SEARCH_HITS}
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
