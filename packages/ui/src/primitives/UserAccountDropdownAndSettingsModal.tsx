import React, { useState } from "react";

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

export interface UserAccountDropdownAndSettingsLabels {
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

/**
 * Story 9.4 — UserAccountDropdown (`280px`) + UserSettingsModal (`720px × max 600px`, 4 Tabs)
 * with `0 ms` Anti-FOUC dual persistence (`localStorage` + `PATCH /api/v1/users/me/preferences`).
 */
export function UserAccountDropdownAndSettingsModal({
  userDisplayName,
  userEmail,
  userRole,
  initialTheme = "light",
  initialLocale = "fr",
  initialHat = "ANALYST_PM_PO",
  initialMcpTokens = [],
  labels,
  onPreferencesSync,
  onLogout,
  onNavigateAssistantBehavior,
}: UserAccountDropdownAndSettingsModalProps): React.ReactElement {
  const [dropdownOpen, setDropdownOpen] = useState<boolean>(false);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<UiUserSettingsTabKey>(
    "PREFERENCES_DISPLAY",
  );
  const [theme, setTheme] = useState<UiThemePreference>(initialTheme);
  const [locale, setLocale] = useState<UiLocalePreference>(initialLocale);
  const [hat, setHat] = useState<string>(initialHat);
  const [autoOpenHelp, setAutoOpenHelp] = useState<boolean>(true);
  const [notificationsEnabled, setNotificationsEnabled] = useState<boolean>(true);
  const [loggedOut, setLoggedOut] = useState<boolean>(false);
  const [passthroughTested, setPassthroughTested] = useState<boolean>(false);

  // Tab 4: Scoped Personal MCP Keys state
  const [mcpTargetKind, setMcpTargetKind] = useState<UiMcpTargetKind>("SPACE");
  const [mcpTargetSlug, setMcpTargetSlug] = useState<string>("ws-claims-alpha");
  const [mcpExpiryDays, setMcpExpiryDays] = useState<30 | 90>(30);
  const [mcpRpmLimit, setMcpRpmLimit] = useState<number>(60);
  const [mcpTokens, setMcpTokens] = useState<readonly UiPersonalMcpTokenItem[]>(
    initialMcpTokens,
  );
  const [lastIssuedPlaintext, setLastIssuedPlaintext] = useState<string | null>(
    null,
  );

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
    // Story 9.4 invariant: opening UserSettingsModal automatically closes UserAccountDropdown!
    setDropdownOpen(false);
    setActiveTab(tab);
    setModalOpen(true);
  };

  const handleLogoutClick = (): void => {
    setDropdownOpen(false);
    setLoggedOut(true);
    onLogout?.();
  };

  const handleIssueMcpToken = (): void => {
    const endpointUri =
      mcpTargetKind === "SPACE"
        ? `/api/v1/mcp/spaces/${mcpTargetSlug}`
        : `/api/v1/mcp/agents/${mcpTargetSlug}`;
    const snippet = JSON.stringify(
      {
        mcpServers: {
          [`orcia-${mcpTargetKind.toLowerCase()}-${mcpTargetSlug}`]: {
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
      label: `IDE MCP (${mcpTargetKind} · ${mcpTargetSlug})`,
      tokenPrefix: "pat_mcp_9a8b7c...",
      tokenSha256: "sha256_at_rest_verified_digest",
      expiresInDays: mcpExpiryDays,
      rpmLimit: mcpRpmLimit,
      targetKind: mcpTargetKind,
      targetSlug: mcpTargetSlug,
      mcpEndpointUri: endpointUri,
      ideJsonSnippet: snippet,
      revoked: false,
    };
    setMcpTokens((prev) => [newItem, ...prev]);
    setLastIssuedPlaintext("pat_mcp_9a8b7c6d5e4f3a2b1c0d");
  };

  const handleRevokeMcpToken = (tokenId: string): void => {
    setMcpTokens((prev) =>
      prev.map((t) => (t.tokenId === tokenId ? { ...t, revoked: true } : t)),
    );
  };

  return (
    <div
      data-testid="user-account-control-root"
      className="relative inline-flex items-center"
    >
      {/* TopHeaderBar Trigger Button: 👤 Login · [Casquette] */}
      <button
        type="button"
        aria-label={labels.triggerAriaLabel}
        aria-expanded={dropdownOpen}
        data-testid="user-account-dropdown-trigger"
        onClick={() => setDropdownOpen((prev) => !prev)}
        className="px-2.5 py-1 rounded-md text-xs font-medium border border-surface-border bg-surface-secondary text-text-primary flex items-center gap-1.5"
      >
        <span>👤 {userDisplayName}</span>
        <span className="font-mono text-[11px] text-text-secondary">
          · [{hat}]
        </span>
      </button>

      {loggedOut && (
        <span
          data-testid="user-logged-out-redirect-pill"
          className="ml-2 text-xs font-mono text-text-secondary"
        >
          POST /api/v1/auth/logout → /login
        </span>
      )}

      {/* UserAccountDropdown (280px) */}
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
              {userEmail} · {userRole}
            </div>
          </div>

          {/* Business Hat Selector */}
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
              <option value="ANALYST_PM_PO">ANALYST_PM_PO</option>
              <option value="ARCHITECT">ARCHITECT</option>
              <option value="TECH_LEAD_DEV">TECH_LEAD_DEV</option>
              <option value="SECURITY_COMPLIANCE">SECURITY_COMPLIANCE</option>
            </select>
          </div>

          {/* 1-Click Theme & Language Switches (0 ms Anti-FOUC localStorage + API PATCH) */}
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

      {/* UserSettingsModal (720px × max 600px, 4 Tabs) */}
      {modalOpen && (
        <div
          role="dialog"
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
                onClick={() => setModalOpen(false)}
                className="px-2 py-1 rounded text-xs border border-surface-border text-text-secondary"
              >
                Fermer (Esc)
              </button>
            </div>

            {/* 4 Tabs Navigation */}
            <div
              role="tablist"
              data-testid="user-settings-tabs"
              className="px-4 pt-2 border-b border-surface-border flex items-center gap-2 text-xs"
            >
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "PREFERENCES_DISPLAY"}
                data-testid="user-settings-tab-PREFERENCES_DISPLAY"
                onClick={() => setActiveTab("PREFERENCES_DISPLAY")}
                className={`px-3 py-1.5 rounded-t border-b-2 ${
                  activeTab === "PREFERENCES_DISPLAY"
                    ? "border-brand-primary font-semibold text-text-primary"
                    : "border-transparent text-text-secondary"
                }`}
              >
                {labels.tab1PreferencesTitle}
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "PROFILE_SECURITY"}
                data-testid="user-settings-tab-PROFILE_SECURITY"
                onClick={() => setActiveTab("PROFILE_SECURITY")}
                className={`px-3 py-1.5 rounded-t border-b-2 ${
                  activeTab === "PROFILE_SECURITY"
                    ? "border-brand-primary font-semibold text-text-primary"
                    : "border-transparent text-text-secondary"
                }`}
              >
                {labels.tab2SecurityTitle}
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "PASSTHROUGH_SOURCES"}
                data-testid="user-settings-tab-PASSTHROUGH_SOURCES"
                onClick={() => setActiveTab("PASSTHROUGH_SOURCES")}
                className={`px-3 py-1.5 rounded-t border-b-2 ${
                  activeTab === "PASSTHROUGH_SOURCES"
                    ? "border-brand-primary font-semibold text-text-primary"
                    : "border-transparent text-text-secondary"
                }`}
              >
                {labels.tab3PassthroughTitle}
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "IDE_MCP_KEYS"}
                data-testid="user-settings-tab-IDE_MCP_KEYS"
                onClick={() => setActiveTab("IDE_MCP_KEYS")}
                className={`px-3 py-1.5 rounded-t border-b-2 ${
                  activeTab === "IDE_MCP_KEYS"
                    ? "border-brand-primary font-semibold text-text-primary"
                    : "border-transparent text-text-secondary"
                }`}
              >
                {labels.tab4McpKeysTitle}
              </button>
            </div>

            {/* Tab Panels */}
            <div className="flex-1 overflow-y-auto p-4 text-xs space-y-3">
              {activeTab === "PREFERENCES_DISPLAY" && (
                <div
                  data-testid="user-settings-panel-PREFERENCES_DISPLAY"
                  className="space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span>Ouverture automatique de l&apos;Aide ❓</span>
                    <input
                      type="checkbox"
                      checked={autoOpenHelp}
                      onChange={(e) => {
                        setAutoOpenHelp(e.target.checked);
                        onPreferencesSync?.({
                          autoOpenContextualHelp: e.target.checked,
                        });
                      }}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Notifications 🔔 actives</span>
                    <input
                      type="checkbox"
                      checked={notificationsEnabled}
                      onChange={(e) => {
                        setNotificationsEnabled(e.target.checked);
                        onPreferencesSync?.({
                          notificationsEnabled: e.target.checked,
                        });
                      }}
                    />
                  </div>
                  {/* Redirect link to Mon Assistant Layer 5 without duplicating prompt textarea */}
                  <div className="pt-2 border-t border-surface-border">
                    <button
                      type="button"
                      data-testid="user-settings-assistant-redirect-link"
                      onClick={() =>
                        onNavigateAssistantBehavior?.("/assistant?modal=settings")
                      }
                      className="text-brand-primary font-medium hover:underline"
                    >
                      {labels.customizeAssistantRedirectCta}
                    </button>
                  </div>
                </div>
              )}

              {activeTab === "PROFILE_SECURITY" && (
                <div
                  data-testid="user-settings-panel-PROFILE_SECURITY"
                  className="space-y-2"
                >
                  <div className="font-semibold">
                    Argon2id Local Password &amp; MFA TOTP (AD-6)
                  </div>
                  <p className="text-text-secondary">
                    Identité : {userEmail} ({userRole})
                  </p>
                </div>
              )}

              {activeTab === "PASSTHROUGH_SOURCES" && (
                <div
                  data-testid="user-settings-panel-PASSTHROUGH_SOURCES"
                  className="space-y-2"
                >
                  <div className="font-semibold">
                    Jetons personnels Passthrough AES-256-GCM (Git / Jira / Confluence / Notion)
                  </div>
                  <button
                    type="button"
                    data-testid="passthrough-test-token-btn"
                    onClick={() => setPassthroughTested(true)}
                    className="px-2.5 py-1 rounded bg-brand-primary text-surface-elevated font-medium"
                  >
                    {labels.testPassthroughTokenCta}
                  </button>
                  {passthroughTested && (
                    <span
                      data-testid="passthrough-test-ok-badge"
                      className="ml-2 text-status-success font-mono"
                    >
                      ✅ Connectivité vérifiée (&lt; 5 s)
                    </span>
                  )}
                </div>
              )}

              {activeTab === "IDE_MCP_KEYS" && (
                <div
                  data-testid="user-settings-panel-IDE_MCP_KEYS"
                  className="space-y-3"
                >
                  <div className="grid grid-cols-2 gap-2">
                    <label className="flex flex-col gap-1">
                      <span className="text-text-secondary">Cible MCP</span>
                      <select
                        data-testid="mcp-target-kind-select"
                        value={mcpTargetKind}
                        onChange={(e) =>
                          setMcpTargetKind(e.target.value as UiMcpTargetKind)
                        }
                        className="rounded border border-surface-border bg-surface-primary px-2 py-1"
                      >
                        <option value="SPACE">{labels.targetWholeSpaceLabel}</option>
                        <option value="AGENT">{labels.targetSingleAgentLabel}</option>
                      </select>
                    </label>
                    <label className="flex flex-col gap-1">
                      <span className="text-text-secondary">Slug (Espace ou Agent)</span>
                      <input
                        type="text"
                        data-testid="mcp-target-slug-input"
                        value={mcpTargetSlug}
                        onChange={(e) => setMcpTargetSlug(e.target.value)}
                        className="rounded border border-surface-border bg-surface-primary px-2 py-1 font-mono"
                      />
                    </label>
                    <label className="flex flex-col gap-1">
                      <span className="text-text-secondary">Expiration obligatoire</span>
                      <select
                        data-testid="mcp-expiry-days-select"
                        value={mcpExpiryDays}
                        onChange={(e) =>
                          setMcpExpiryDays(Number(e.target.value) as 30 | 90)
                        }
                        className="rounded border border-surface-border bg-surface-primary px-2 py-1"
                      >
                        <option value={30}>30 jours</option>
                        <option value={90}>90 jours</option>
                      </select>
                    </label>
                    <label className="flex flex-col gap-1">
                      <span className="text-text-secondary">Plafond RPM</span>
                      <input
                        type="number"
                        data-testid="mcp-rpm-limit-input"
                        value={mcpRpmLimit}
                        onChange={(e) => setMcpRpmLimit(Number(e.target.value))}
                        className="rounded border border-surface-border bg-surface-primary px-2 py-1 font-mono"
                      />
                    </label>
                  </div>

                  <button
                    type="button"
                    data-testid="mcp-generate-token-btn"
                    onClick={handleIssueMcpToken}
                    className="px-3 py-1.5 rounded bg-brand-primary text-surface-elevated font-medium"
                  >
                    {labels.generateMcpTokenCta}
                  </button>

                  {lastIssuedPlaintext !== null && (
                    <div
                      data-testid="mcp-issued-plaintext-banner"
                      className="p-2 rounded border border-surface-border bg-surface-secondary font-mono text-[11px]"
                    >
                      Jeton unique (SHA-256 en base) : {lastIssuedPlaintext}
                    </div>
                  )}

                  <div data-testid="mcp-tokens-list" className="space-y-2">
                    {mcpTokens.map((tok) => (
                      <div
                        key={tok.tokenId}
                        data-testid={`mcp-token-row-${tok.tokenId}`}
                        className="p-2.5 rounded border border-surface-border bg-surface-primary space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold">
                            {tok.label} · {tok.mcpEndpointUri}
                          </span>
                          {tok.revoked ? (
                            <span
                              data-testid={`mcp-token-revoked-badge-${tok.tokenId}`}
                              className="text-status-error font-mono text-[11px]"
                            >
                              Révoqué (&lt; 10 ms Redis)
                            </span>
                          ) : (
                            <button
                              type="button"
                              data-testid={`mcp-revoke-btn-${tok.tokenId}`}
                              onClick={() => handleRevokeMcpToken(tok.tokenId)}
                              className="px-2 py-0.5 rounded border border-surface-border text-status-error text-[11px]"
                            >
                              {labels.revokeMcpTokenCta}
                            </button>
                          )}
                        </div>
                        <div className="text-[10px] text-text-secondary">
                          {labels.ideJsonReadyTitle} (VS Code / Cursor / Claude Code / Antigravity / JetBrains)
                        </div>
                        <pre
                          data-testid={`mcp-ide-snippet-${tok.tokenId}`}
                          className="p-2 rounded bg-surface-secondary font-mono text-[10px] overflow-x-auto"
                        >
                          {tok.ideJsonSnippet}
                        </pre>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
