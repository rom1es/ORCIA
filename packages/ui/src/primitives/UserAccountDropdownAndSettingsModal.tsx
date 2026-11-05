import React, { useEffect, useState } from "react";
import {
  RgaaDialogFooterActions,
  RgaaUnsavedChangesAlert,
  resolveRgaaModalGuardLabels,
  useUnsavedChangesDialogGuard,
  type RgaaModalGuardLabels,
} from "../components/RgaaModalDialog";
import { UserSettingsModalTabs } from "./UserSettingsModalTabs";

export type UiThemePreference = "light" | "dark" | "system";
export type UiLocalePreference = "fr" | "en";
export type UiUserSettingsTabKey =
  | "PREFERENCES_DISPLAY"
  | "PROFILE_SECURITY"
  | "PASSTHROUGH_SOURCES"
  | "IDE_MCP_KEYS";

export type UiMcpTargetKind = "SPACE" | "AGENT";

export interface UiPersonalMcpTokenItem {
  readonly tokenId: string;
  readonly label: string;
  readonly tokenPrefix: string;
  readonly tokenSha256: string;
  readonly expiresInDays: 30 | 90;
  readonly rpmLimit: number;
  readonly targetKind: UiMcpTargetKind;
  readonly targetSlug: string;
  readonly mcpEndpointUri: string;
  readonly ideJsonSnippet: string;
  readonly revoked: boolean;
}

export interface UserAccountDropdownAndSettingsLabels extends RgaaModalGuardLabels {
  readonly triggerAriaLabel: string;
  readonly dropdownWidthNote: string;
  readonly hatSelectorLabel: string;
  readonly themeQuickToggleLabel: string;
  readonly localeQuickToggleLabel: string;
  readonly openAccountSettingsLabel: string;
  readonly openPassthroughSourcesLabel: string;
  readonly logoutButtonLabel: string;
  readonly modalTitle: string;
  readonly tab1PreferencesTitle: string;
  readonly tab2SecurityTitle: string;
  readonly tab3PassthroughTitle: string;
  readonly tab4McpKeysTitle: string;
  readonly customizeAssistantRedirectCta: string;
  readonly testPassthroughTokenCta: string;
  readonly generateMcpTokenCta: string;
  readonly revokeMcpTokenCta: string;
  readonly targetWholeSpaceLabel: string;
  readonly targetSingleAgentLabel: string;
  readonly ideJsonReadyTitle: string;
}

export interface UserAccountPreferencesPatch {
  readonly theme?: UiThemePreference;
  readonly locale?: UiLocalePreference;
  readonly defaultHat?: string;
  readonly autoOpenContextualHelp?: boolean;
  readonly notificationsEnabled?: boolean;
}

export interface UserAccountDropdownAndSettingsModalProps {
  readonly userDisplayName: string;
  readonly userEmail: string;
  readonly userRole: string;
  readonly initialTheme?: UiThemePreference;
  readonly initialLocale?: UiLocalePreference;
  readonly initialHat?: string;
  readonly initialMcpTokens?: readonly UiPersonalMcpTokenItem[];
  readonly labels: UserAccountDropdownAndSettingsLabels;
  readonly onPreferencesSync?: (patch: UserAccountPreferencesPatch) => void;
  readonly onLogout?: () => void;
  readonly onNavigateAssistantBehavior?: (redirectUri: string) => void;
}

export const ROLE_DISPLAY_LABELS_FR: Record<string, string> = {
  PLATFORM_ADMIN: "Administrateur de la plateforme",
  ANALYST_PM_PO: "Product Manager / Métier",
  ARCHITECT: "Architecte",
  TECH_LEAD_DEV: "Tech Lead / Développeur",
  SECURITY_COMPLIANCE: "Sécurité & Conformité",
};

export function UserAccountDropdownAndSettingsModal({
  userDisplayName,
  userEmail,
  userRole,
  initialTheme = "light",
  initialLocale = "fr",
  initialHat,
  initialMcpTokens = [],
  labels,
  onPreferencesSync,
  onLogout,
  onNavigateAssistantBehavior,
}: UserAccountDropdownAndSettingsModalProps): React.ReactElement {
  const defaultRoleKey =
    initialHat ?? (userRole === "PLATFORM_ADMIN" ? "PLATFORM_ADMIN" : "ANALYST_PM_PO");
  const [dropdownOpen, setDropdownOpen] = useState<boolean>(false);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<UiUserSettingsTabKey>(
    "PREFERENCES_DISPLAY",
  );
  const [theme, setTheme] = useState<UiThemePreference>(initialTheme);
  const [locale, setLocale] = useState<UiLocalePreference>(initialLocale);
  const [hat, setHat] = useState<string>(defaultRoleKey);
  const [autoOpenHelp, setAutoOpenHelp] = useState<boolean>(true);
  const [notificationsEnabled, setNotificationsEnabled] = useState<boolean>(true);
  const [loggedOut, setLoggedOut] = useState<boolean>(false);
  const [passthroughTested, setPassthroughTested] = useState<boolean>(false);

  // Tab 4: Scoped Personal MCP Keys state
  const [mcpTargetKind, setMcpTargetKind] = useState<UiMcpTargetKind>("SPACE");
  const [mcpTargetSlug, setMcpTargetSlug] = useState<string>("");
  const [mcpExpiryDays, setMcpExpiryDays] = useState<30 | 90>(30);
  const [mcpRpmLimit, setMcpRpmLimit] = useState<number>(60);
  const [mcpTokens, setMcpTokens] = useState<readonly UiPersonalMcpTokenItem[]>(
    initialMcpTokens,
  );
  const [lastIssuedPlaintext, setLastIssuedPlaintext] = useState<string | null>(
    null,
  );
  const [isDirty, setIsDirty] = useState<boolean>(false);

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

  const handleToggleThemeQuick = (): void => {
    const nextTheme: UiThemePreference = theme === "light" ? "dark" : "light";
    setTheme(nextTheme);
    persistZeroMsAntiFouc(nextTheme, locale, { theme: nextTheme });
  };

  const handleToggleLocaleQuick = (): void => {
    const nextLocale: UiLocalePreference = locale === "fr" ? "en" : "fr";
    setLocale(nextLocale);
    persistZeroMsAntiFouc(theme, nextLocale, { locale: nextLocale });
  };

  const handleOpenSettingsModal = (tab: UiUserSettingsTabKey): void => {
    setDropdownOpen(false);
    setActiveTab(tab);
    setIsDirty(false);
    setModalOpen(true);
  };

  const handleLogoutClick = (): void => {
    setDropdownOpen(false);
    setLoggedOut(true);
    onLogout?.();
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

  const handleRevokeMcpToken = (tokenId: string): void => {
    setMcpTokens((prev) =>
      prev.map((t) => (t.tokenId === tokenId ? { ...t, revoked: true } : t)),
    );
  };

  const handleSaveModalChanges = (): void => {
    onPreferencesSync?.({
      theme,
      locale,
      defaultHat: hat,
      autoOpenContextualHelp: autoOpenHelp,
      notificationsEnabled,
    });
    setIsDirty(false);
    setModalOpen(false);
  };

  const displayRoleLabel = ROLE_DISPLAY_LABELS_FR[hat] ?? hat;

  return (
    <div
      data-testid="user-account-control-root"
      className="relative inline-flex items-center"
    >
      {/* TopHeaderBar Trigger Button: 👤 Nom · Rôle */}
      <button
        type="button"
        aria-label={labels.triggerAriaLabel}
        aria-expanded={dropdownOpen}
        data-testid="user-account-dropdown-trigger"
        onClick={() => setDropdownOpen((prev) => !prev)}
        className="px-2.5 py-1 rounded-md text-xs font-medium border border-surface-border bg-surface-secondary text-text-primary flex items-center gap-1.5"
      >
        <span>👤 {userDisplayName}</span>
        <span
          data-testid="user-account-role-pill"
          className="text-[11px] text-text-secondary"
        >
          · {displayRoleLabel}
        </span>
      </button>

      {loggedOut && (
        <span
          data-testid="user-logged-out-redirect-pill"
          className="ml-2 text-xs text-text-secondary"
        >
          Déconnecté
        </span>
      )}

      {/* UserAccountDropdown */}
      {dropdownOpen && (
        <div
          role="menu"
          aria-label="UserAccountDropdown"
          data-testid="user-account-dropdown-menu"
          className="absolute right-0 top-10 z-30 w-[280px] rounded-xl border border-surface-border bg-surface-elevated p-3 shadow-lg space-y-2.5 text-xs text-text-primary"
        >
          <div className="border-b border-surface-border pb-2">
            <div className="font-semibold">{userDisplayName}</div>
            <div className="text-[11px] text-text-secondary">
              {userEmail} · {ROLE_DISPLAY_LABELS_FR[userRole] ?? userRole}
            </div>
          </div>

          {/* Role Selector */}
          <div className="flex items-center justify-between gap-2">
            <span className="text-text-secondary">{labels.hatSelectorLabel}</span>
            <select
              aria-label={labels.hatSelectorLabel}
              data-testid="dropdown-hat-selector"
              value={hat}
              onChange={(e) => {
                const nextHat = e.target.value;
                setHat(nextHat);
                onPreferencesSync?.({ defaultHat: nextHat });
              }}
              className="rounded border border-surface-border bg-surface-primary px-1.5 py-0.5 text-xs"
            >
              <option value="PLATFORM_ADMIN">Administrateur de la plateforme</option>
              <option value="ANALYST_PM_PO">Product Manager / Métier</option>
              <option value="ARCHITECT">Architecte</option>
              <option value="TECH_LEAD_DEV">Tech Lead / Développeur</option>
              <option value="SECURITY_COMPLIANCE">Sécurité &amp; Conformité</option>
            </select>
          </div>

          {/* 1-Click Theme & Language Switches */}
          <div className="flex items-center justify-between gap-2">
            <span>{labels.themeQuickToggleLabel}</span>
            <button
              type="button"
              data-testid="dropdown-quick-theme-switch"
              onClick={handleToggleThemeQuick}
              className="px-2 py-0.5 rounded border border-surface-border bg-surface-secondary font-mono text-[11px]"
            >
              {theme === "light" ? "☀️ Clair" : "🌙 Sombre"}
            </button>
          </div>

          <div className="flex items-center justify-between gap-2">
            <span>{labels.localeQuickToggleLabel}</span>
            <button
              type="button"
              data-testid="dropdown-quick-locale-switch"
              onClick={handleToggleLocaleQuick}
              className="px-2 py-0.5 rounded border border-surface-border bg-surface-secondary font-mono text-[11px]"
            >
              {locale.toUpperCase()}
            </button>
          </div>

          <div className="border-t border-surface-border pt-2 space-y-1">
            <button
              type="button"
              data-testid="dropdown-open-settings-modal-btn"
              onClick={() => handleOpenSettingsModal("PREFERENCES_DISPLAY")}
              className="w-full text-left px-2 py-1.5 rounded hover:bg-surface-secondary flex items-center justify-between"
            >
              <span>{labels.openAccountSettingsLabel}</span>
              <span className="font-mono text-[10px] text-text-secondary">
                g u
              </span>
            </button>
            <button
              type="button"
              data-testid="dropdown-open-passthrough-btn"
              onClick={() => handleOpenSettingsModal("PASSTHROUGH_SOURCES")}
              className="w-full text-left px-2 py-1.5 rounded hover:bg-surface-secondary"
            >
              {labels.openPassthroughSourcesLabel}
            </button>
          </div>

          <div className="border-t border-surface-border pt-2">
            <button
              type="button"
              data-testid="dropdown-logout-btn"
              onClick={handleLogoutClick}
              className="w-full text-left px-2 py-1.5 rounded font-medium text-status-error hover:bg-surface-secondary"
            >
              {labels.logoutButtonLabel}
            </button>
          </div>
        </div>
      )}

      {/* UserSettingsModal */}
      {modalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={labels.modalTitle}
          data-testid="user-settings-modal"
          className="fixed inset-0 z-40 flex items-center justify-center bg-surface-primary/80 p-4"
        >
          <div className="w-[720px] max-h-[600px] flex flex-col rounded-xl border border-surface-border bg-surface-elevated text-text-primary shadow-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-surface-border flex items-center justify-between">
              <h2 className="text-sm font-semibold">{labels.modalTitle}</h2>
              <button
                type="button"
                data-testid="user-settings-modal-close-btn"
                onClick={requestClose}
                className="px-2 py-1 rounded text-xs border border-surface-border text-text-secondary"
              >
                Fermer (Esc)
              </button>
            </div>

            <div className="px-4 pt-2">
              <RgaaUnsavedChangesAlert
                testIdPrefix="user-settings-modal"
                isOpen={showUnsavedAlert}
                labels={guardLabels}
                locale={locale}
                onStay={cancelDiscard}
                onConfirmDiscard={confirmDiscard}
              />
            </div>

            {/* 4 Tabs Navigation */}
            <div
              role="tablist"
              data-testid="user-settings-tabs"
              className="orcia-ds-tabs px-4 pt-2 pb-2 border-b border-surface-border items-center text-xs"
            >
              {(
                [
                  ["PREFERENCES_DISPLAY", labels.tab1PreferencesTitle],
                  ["PROFILE_SECURITY", labels.tab2SecurityTitle],
                  ["PASSTHROUGH_SOURCES", labels.tab3PassthroughTitle],
                  ["IDE_MCP_KEYS", labels.tab4McpKeysTitle],
                ] as const
              ).map(([tabKey, tabLabel]) => (
                <button
                  key={tabKey}
                  type="button"
                  role="tab"
                  aria-selected={activeTab === tabKey}
                  data-testid={`user-settings-tab-${tabKey}`}
                  onClick={() => setActiveTab(tabKey)}
                  className="orcia-ds-tab"
                >
                  {tabLabel}
                </button>
              ))}
            </div>

            <UserSettingsModalTabs
              activeTab={activeTab}
              userEmail={userEmail}
              userRole={userRole}
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
              onRevokeMcpToken={handleRevokeMcpToken}
            />

            <div className="px-4 py-3 border-t border-surface-border bg-surface-secondary">
              <RgaaDialogFooterActions
                testIdPrefix="user-settings-modal"
                cancelLabel={guardLabels.cancelButtonLabel}
                submitLabel={guardLabels.submitButtonLabel}
                onCancel={requestClose}
                onSubmit={handleSaveModalChanges}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
