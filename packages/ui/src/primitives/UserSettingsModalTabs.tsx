import React from "react";
import type {
  UiMcpTargetKind,
  UiPersonalMcpTokenItem,
  UiUserSettingsTabKey,
  UserAccountDropdownAndSettingsLabels,
  UserAccountPreferencesPatch,
} from "./UserAccountDropdownAndSettingsModal";

export interface UserSettingsModalTabsProps {
  readonly activeTab: UiUserSettingsTabKey;
  readonly userEmail: string;
  readonly userRole: string;
  readonly autoOpenHelp: boolean;
  readonly notificationsEnabled: boolean;
  readonly passthroughTested: boolean;
  readonly mcpTargetKind: UiMcpTargetKind;
  readonly mcpTargetSlug: string;
  readonly mcpExpiryDays: 30 | 90;
  readonly mcpRpmLimit: number;
  readonly mcpTokens: readonly UiPersonalMcpTokenItem[];
  readonly lastIssuedPlaintext: string | null;
  readonly labels: UserAccountDropdownAndSettingsLabels;
  readonly onChangeAutoOpenHelp: (next: boolean) => void;
  readonly onChangeNotificationsEnabled: (next: boolean) => void;
  readonly onPreferencesSync?: (patch: UserAccountPreferencesPatch) => void;
  readonly onNavigateAssistantBehavior?: (redirectUri: string) => void;
  readonly onTestPassthrough: () => void;
  readonly onChangeMcpTargetKind: (kind: UiMcpTargetKind) => void;
  readonly onChangeMcpTargetSlug: (slug: string) => void;
  readonly onChangeMcpExpiryDays: (days: 30 | 90) => void;
  readonly onChangeMcpRpmLimit: (rpm: number) => void;
  readonly onIssueMcpToken: () => void;
  readonly onRevokeMcpToken: (tokenId: string) => void;
}

export function UserSettingsModalTabs({
  activeTab,
  userEmail,
  userRole,
  autoOpenHelp,
  notificationsEnabled,
  passthroughTested,
  mcpTargetKind,
  mcpTargetSlug,
  mcpExpiryDays,
  mcpRpmLimit,
  mcpTokens,
  lastIssuedPlaintext,
  labels,
  onChangeAutoOpenHelp,
  onChangeNotificationsEnabled,
  onPreferencesSync,
  onNavigateAssistantBehavior,
  onTestPassthrough,
  onChangeMcpTargetKind,
  onChangeMcpTargetSlug,
  onChangeMcpExpiryDays,
  onChangeMcpRpmLimit,
  onIssueMcpToken,
  onRevokeMcpToken,
}: UserSettingsModalTabsProps): React.ReactElement {
  return (
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
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              checked={autoOpenHelp}
              onChange={(e) => {
                onChangeAutoOpenHelp(e.target.checked);
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
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              checked={notificationsEnabled}
              onChange={(e) => {
                onChangeNotificationsEnabled(e.target.checked);
                onPreferencesSync?.({
                  notificationsEnabled: e.target.checked,
                });
              }}
            />
          </div>
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
            Authentification locale &amp; double facteur TOTP
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
            Jetons personnels Passthrough (Git / Jira / Confluence / Notion)
          </div>
          <button
            type="button"
            data-testid="passthrough-test-token-btn"
            onClick={onTestPassthrough}
            className="px-2.5 py-1 rounded bg-brand-primary text-surface-elevated font-medium"
          >
            {labels.testPassthroughTokenCta}
          </button>
          {passthroughTested && (
            <span
              data-testid="passthrough-test-ok-badge"
              className="ml-2 text-status-success font-mono"
            >
              ✅ Connectivité vérifiée
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
                  onChangeMcpTargetKind(e.target.value as UiMcpTargetKind)
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
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="mcp-target-slug-input"
                value={mcpTargetSlug}
                onChange={(e) => onChangeMcpTargetSlug(e.target.value)}
                placeholder="ex: mon-espace"
                className="rounded border border-surface-border bg-surface-primary px-2 py-1 font-mono"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-text-secondary">Expiration obligatoire</span>
              <select
                data-testid="mcp-expiry-days-select"
                value={mcpExpiryDays}
                onChange={(e) =>
                  onChangeMcpExpiryDays(Number(e.target.value) as 30 | 90)
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
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="mcp-rpm-limit-input"
                value={mcpRpmLimit}
                onChange={(e) => onChangeMcpRpmLimit(Number(e.target.value))}
                className="rounded border border-surface-border bg-surface-primary px-2 py-1 font-mono"
              />
            </label>
          </div>

          <button
            type="button"
            data-testid="mcp-generate-token-btn"
            onClick={onIssueMcpToken}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                e.stopPropagation();
                onIssueMcpToken();
              }
            }}
            className="px-3 py-1.5 rounded bg-brand-primary text-surface-elevated font-medium"
          >
            {labels.generateMcpTokenCta}
          </button>

          {lastIssuedPlaintext !== null && (
            <div
              data-testid="mcp-issued-plaintext-banner"
              className="p-2 rounded border border-surface-border bg-surface-secondary font-mono text-[11px]"
            >
              Jeton unique : {lastIssuedPlaintext}
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
                      Révoqué
                    </span>
                  ) : (
                    <button
                      type="button"
                      data-testid={`mcp-revoke-btn-${tok.tokenId}`}
                      onClick={() => onRevokeMcpToken(tok.tokenId)}
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
  );
}
