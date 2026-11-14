import React, { useEffect, useState } from "react";
import { OrciaIcon } from "../components/icons";
import {
  resolveRgaaModalGuardLabels,
  useUnsavedChangesDialogGuard,
} from "../components/RgaaModalDialog";
import { UserAccountDropdownMenu } from "./UserAccountDropdownMenu";
import {
  type UiLocalePreference,
  type UiMcpTargetKind,
  type UiPersonalMcpTokenItem,
  type UiThemePreference,
  type UiUserAccountOrgUnitView,
  type UiUserAccountProfileView,
  type UiUserPassthroughConnectorView,
  type UiUserSettingsTabKey,
  type UserAccountDropdownAndSettingsLabels,
  type UserAccountDropdownAndSettingsModalProps,
  type UserAccountPreferencesPatch,
} from "./UserAccountDropdownTypes";
import { UserSettingsModalDialog } from "./UserSettingsModalDialog";

export type {
  UiLocalePreference,
  UiMcpTargetKind,
  UiPersonalMcpTokenItem,
  UiThemePreference,
  UiUserAccountOrgUnitView,
  UiUserAccountProfileView,
  UiUserPassthroughConnectorView,
  UiUserSettingsTabKey,
  UserAccountDropdownAndSettingsLabels,
  UserAccountDropdownAndSettingsModalProps,
  UserAccountPreferencesPatch,
};

export const ROLE_DISPLAY_LABELS_FR: Record<string, string> = {
  PLATFORM_ADMIN: "Administrateur de la plateforme",
  SECOPS: "Responsable Sécurité & Habilitations",
  BU_LEAD: "Responsable de Direction (BU)",
  TEAM_LEAD: "Responsable d'Équipe",
  CONTRIBUTOR: "Contributeur",
  OBSERVER: "Observateur (Lecture seule)",
  READ_ONLY_OBSERVER: "Observateur (Lecture seule)",
  ANALYST_PM_PO: "Product Manager / Métier",
  ARCHITECT: "Architecte",
  TECH_LEAD_DEV: "Tech Lead / Développeur",
  SECURITY_COMPLIANCE: "Sécurité & Conformité",
};

export const ROLE_DISPLAY_LABELS_EN: Record<string, string> = {
  PLATFORM_ADMIN: "Platform Administrator",
  SECOPS: "Security & Access Officer",
  BU_LEAD: "Business Unit Lead",
  TEAM_LEAD: "Team Lead",
  CONTRIBUTOR: "Contributor",
  OBSERVER: "Observer (Read-only)",
  READ_ONLY_OBSERVER: "Observer (Read-only)",
  ANALYST_PM_PO: "Product Manager / Business",
  ARCHITECT: "Architect",
  TECH_LEAD_DEV: "Tech Lead / Developer",
  SECURITY_COMPLIANCE: "Security & Compliance",
};

export function resolveUserRoleDisplayLabel(
  roleKey: string,
  locale: UiLocalePreference = "fr",
): string {
  const map = locale === "en" ? ROLE_DISPLAY_LABELS_EN : ROLE_DISPLAY_LABELS_FR;
  return map[roleKey] ?? roleKey;
}

export function UserAccountDropdownAndSettingsModal({
  userDisplayName,
  userEmail,
  userRole,
  initialTheme = "light",
  initialLocale = "fr",
  initialHat,
  initialMcpTokens = [],
  initialTab,
  activeTab: controlledActiveTab,
  onActiveTabChange,
  modalOpen: controlledModalOpen,
  onModalOpenChange,
  labels,
  accountProfile,
  passthroughConnectors,
  onPreferencesSync,
  onLogout,
  onNavigateAssistantBehavior,
  onSavePassthroughToken,
  onRevokePassthroughToken,
}: UserAccountDropdownAndSettingsModalProps): React.ReactElement {
  const defaultRoleKey =
    initialHat ?? (userRole in ROLE_DISPLAY_LABELS_FR ? userRole : "ANALYST_PM_PO");
  const [dropdownOpen, setDropdownOpen] = useState<boolean>(false);
  const [internalModalOpen, setInternalModalOpen] = useState<boolean>(false);
  const [internalActiveTab, setInternalActiveTab] = useState<UiUserSettingsTabKey>(
    initialTab ?? "PREFERENCES_DISPLAY",
  );
  const activeTab = controlledActiveTab !== undefined ? controlledActiveTab : internalActiveTab;
  const setActiveTab = (tab: UiUserSettingsTabKey): void => {
    setInternalActiveTab(tab);
    onActiveTabChange?.(tab);
  };
  const [theme, setTheme] = useState<UiThemePreference>(initialTheme);
  const [locale, setLocale] = useState<UiLocalePreference>(initialLocale);
  const [hat, setHat] = useState<string>(defaultRoleKey);
  const [autoOpenHelp, setAutoOpenHelp] = useState<boolean>(true);
  const [notificationsEnabled, setNotificationsEnabled] = useState<boolean>(true);
  const [loggedOut, setLoggedOut] = useState<boolean>(false);
  const [passthroughTested, setPassthroughTested] = useState<boolean>(false);

  const [mcpTargetKind, setMcpTargetKind] = useState<UiMcpTargetKind>("SPACE");
  const [mcpTargetSlug, setMcpTargetSlug] = useState<string>("");
  const [mcpExpiryDays, setMcpExpiryDays] = useState<30 | 90>(30);
  const [mcpRpmLimit, setMcpRpmLimit] = useState<number>(60);
  const [mcpTokens, setMcpTokens] = useState<readonly UiPersonalMcpTokenItem[]>(initialMcpTokens);
  const [lastIssuedPlaintext, setLastIssuedPlaintext] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState<boolean>(false);

  const modalOpen = controlledModalOpen !== undefined ? controlledModalOpen : internalModalOpen;
  const setModalOpen = (next: boolean): void => {
    setInternalModalOpen(next);
    onModalOpenChange?.(next);
  };

  useEffect(() => {
    if (initialHat) {
      setHat(initialHat);
    }
  }, [initialHat]);

  useEffect(() => {
    if (initialTab) {
      setInternalActiveTab(initialTab);
    }
  }, [initialTab]);

  useEffect(() => {
    setLocale(initialLocale);
  }, [initialLocale]);

  const guardLabels = resolveRgaaModalGuardLabels(labels, locale);

  const resetUnsavedDrafts = (): void => {
    setMcpTargetSlug("");
    setMcpTargetKind("SPACE");
    setMcpExpiryDays(30);
    setMcpRpmLimit(60);
    setIsDirty(false);
  };

  const { showUnsavedAlert, requestClose, cancelDiscard, confirmDiscard } =
    useUnsavedChangesDialogGuard({
      isOpen: modalOpen,
      isDirty,
      onClose: () => setModalOpen(false),
      onDiscardChanges: resetUnsavedDrafts,
    });

  useEffect(() => {
    if (!dropdownOpen || modalOpen) {
      return;
    }
    const handleDropdownKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setDropdownOpen(false);
      }
    };
    window.addEventListener("keydown", handleDropdownKeyDown);
    return () => window.removeEventListener("keydown", handleDropdownKeyDown);
  }, [dropdownOpen, modalOpen]);

  const persistZeroMsAntiFouc = (
    nextTheme: UiThemePreference,
    nextLocale: UiLocalePreference,
    patch: UserAccountPreferencesPatch,
  ): void => {
    document.documentElement.dataset.theme = nextTheme;
    document.documentElement.lang = nextLocale;
    try {
      if (typeof window.localStorage?.setItem === "function") {
        window.localStorage.setItem("orcia_theme", nextTheme);
        window.localStorage.setItem("orcia_locale", nextLocale);
      }
    } catch {
      // Safe fallback in restricted storage environments
    }
    onPreferencesSync?.(patch);
  };

  const handleOpenSettingsModal = (tab: UiUserSettingsTabKey): void => {
    setDropdownOpen(false);
    setActiveTab(tab);
    setIsDirty(false);
    setModalOpen(true);
  };

  const handleIssueMcpToken = (): void => {
    const resolvedSlug = mcpTargetSlug.trim() || "default";
    const endpointUri =
      mcpTargetKind === "SPACE"
        ? `/api/v1/mcp/spaces/${resolvedSlug}`
        : `/api/v1/mcp/agents/${resolvedSlug}`;
    const snippet = JSON.stringify(
      {
        mcpServers: {
          [`orcia-${mcpTargetKind.toLowerCase()}-${resolvedSlug}`]: {
            url: `https://orcia.internal${endpointUri}`,
            headers: { Authorization: "Bearer ${ORCIA_MCP_PAT}" },
          },
        },
      },
      null,
      2,
    );
    const newItem: UiPersonalMcpTokenItem = {
      tokenId: `mcp-tok-${mcpTokens.length + 1}`,
      label: `IDE MCP (${mcpTargetKind} · ${resolvedSlug})`,
      tokenPrefix: "pat_mcp_9a8b7c...",
      tokenSha256: "sha256_at_rest_verified_digest",
      expiresInDays: mcpExpiryDays,
      rpmLimit: mcpRpmLimit,
      targetKind: mcpTargetKind,
      targetSlug: resolvedSlug,
      mcpEndpointUri: endpointUri,
      ideJsonSnippet: snippet,
      revoked: false,
    };
    setMcpTokens((prev) => [newItem, ...prev]);
    setLastIssuedPlaintext("pat_mcp_9a8b7c6d5e4f3a2b1c0d");
    setIsDirty(false);
  };

  const displayRoleLabel = resolveUserRoleDisplayLabel(hat, locale);
  const roleMap = locale === "en" ? ROLE_DISPLAY_LABELS_EN : ROLE_DISPLAY_LABELS_FR;

  return (
    <div data-testid="user-account-control-root" className="relative inline-flex items-center">
      <button
        type="button"
        aria-label={labels.triggerAriaLabel}
        aria-expanded={dropdownOpen}
        data-testid="user-account-dropdown-trigger"
        onClick={() => setDropdownOpen((prev) => !prev)}
        className="px-2.5 py-1 rounded-md text-xs font-medium border border-surface-border bg-surface-secondary text-text-primary flex items-center gap-1.5"
      >
        <span className="inline-flex items-center gap-1.5">
          <OrciaIcon name="user" size={15} />
          <span>{userDisplayName}</span>
        </span>
        <span data-testid="user-account-role-pill" className="text-[11px] text-text-secondary">
          · {displayRoleLabel}
        </span>
      </button>

      {loggedOut && (
        <span data-testid="user-logged-out-redirect-pill" className="ml-2 text-xs text-text-secondary">
          {locale === "en" ? "Signed out" : "Déconnecté"}
        </span>
      )}

      {dropdownOpen && (
        <UserAccountDropdownMenu
          userDisplayName={userDisplayName}
          userEmail={userEmail}
          userRole={userRole}
          hat={hat}
          theme={theme}
          locale={locale}
          roleMap={roleMap}
          labels={labels}
          onChangeHat={(nextHat) => {
            setHat(nextHat);
            onPreferencesSync?.({ defaultHat: nextHat });
          }}
          onToggleTheme={() => {
            const nextTheme: UiThemePreference = theme === "light" ? "dark" : "light";
            setTheme(nextTheme);
            persistZeroMsAntiFouc(nextTheme, locale, { theme: nextTheme });
          }}
          onToggleLocale={() => {
            const nextLocale: UiLocalePreference = locale === "fr" ? "en" : "fr";
            setLocale(nextLocale);
            persistZeroMsAntiFouc(theme, nextLocale, { locale: nextLocale });
          }}
          onOpenSettingsModal={handleOpenSettingsModal}
          onLogoutClick={() => {
            setDropdownOpen(false);
            setLoggedOut(true);
            onLogout?.();
          }}
        />
      )}

      {modalOpen && (
        <UserSettingsModalDialog
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          userEmail={userEmail}
          userRole={userRole}
          locale={locale}
          autoOpenHelp={autoOpenHelp}
          notificationsEnabled={notificationsEnabled}
          passthroughTested={passthroughTested}
          mcpTargetKind={mcpTargetKind}
          mcpTargetSlug={mcpTargetSlug}
          mcpExpiryDays={mcpExpiryDays}
          mcpRpmLimit={mcpRpmLimit}
          mcpTokens={mcpTokens}
          lastIssuedPlaintext={lastIssuedPlaintext}
          labels={labels}
          guardLabels={guardLabels}
          showUnsavedAlert={showUnsavedAlert}
          accountProfile={accountProfile}
          passthroughConnectors={passthroughConnectors}
          onRequestClose={requestClose}
          onCancelDiscard={cancelDiscard}
          onConfirmDiscard={confirmDiscard}
          onSaveChanges={() => {
            onPreferencesSync?.({
              theme,
              locale,
              defaultHat: hat,
              autoOpenContextualHelp: autoOpenHelp,
              notificationsEnabled,
            });
            setIsDirty(false);
            setModalOpen(false);
          }}
          onChangeAutoOpenHelp={(next) => {
            setAutoOpenHelp(next);
            setIsDirty(true);
          }}
          onChangeNotificationsEnabled={(next) => {
            setNotificationsEnabled(next);
            setIsDirty(true);
          }}
          onPreferencesSync={onPreferencesSync}
          onNavigateAssistantBehavior={onNavigateAssistantBehavior}
          onTestPassthrough={() => setPassthroughTested(true)}
          onSavePassthroughToken={onSavePassthroughToken}
          onRevokePassthroughToken={onRevokePassthroughToken}
          onChangeMcpTargetKind={(kind) => {
            setMcpTargetKind(kind);
            setIsDirty(true);
          }}
          onChangeMcpTargetSlug={(slug) => {
            setMcpTargetSlug(slug);
            setIsDirty(slug.trim().length > 0);
          }}
          onChangeMcpExpiryDays={(days) => {
            setMcpExpiryDays(days);
            setIsDirty(true);
          }}
          onChangeMcpRpmLimit={(rpm) => {
            setMcpRpmLimit(rpm);
            setIsDirty(true);
          }}
          onIssueMcpToken={handleIssueMcpToken}
          onRevokeMcpToken={(tokenId) => {
            setMcpTokens((prev) =>
              prev.map((t) => (t.tokenId === tokenId ? { ...t, revoked: true } : t)),
            );
          }}
        />
      )}
    </div>
  );
}
