/**
 * Types and interfaces for User Account dropdown, profile & passthrough tokens (`AD-21`, `Story 17.4`).
 *
 * Isolated in `packages/ui` — zero imports of `@orcia/api-client` or `@tanstack/react-router`.
 */

import type { RgaaModalGuardLabels } from "../components/RgaaModalDialog";

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

export interface UiUserAccountOrgUnitView {
  readonly id: string;
  readonly slug: string;
  readonly name: string;
  readonly unitType: string;
  readonly billingEnabled: boolean;
  readonly isLead?: boolean;
}

export interface UiUserAccountProfileView {
  readonly principalId: string;
  readonly displayName: string;
  readonly email: string;
  readonly roles: readonly string[];
  readonly teams: readonly UiUserAccountOrgUnitView[];
  readonly billingOrgUnits: readonly UiUserAccountOrgUnitView[];
}

export interface UiUserPassthroughConnectorView {
  readonly connectorId: string;
  readonly connectorName: string;
  readonly connectorKind: string;
  readonly baseUrl: string;
  readonly authMode: string;
  readonly connected: boolean;
  readonly externalAuthorLogin?: string | null;
  readonly secretStatus: {
    readonly configured: boolean;
    readonly fingerprint?: string | null;
    readonly updatedAtIso?: string | null;
  };
}

export interface UserAccountDropdownAndSettingsModalProps {
  readonly userDisplayName: string;
  readonly userEmail: string;
  readonly userRole: string;
  readonly initialTheme?: UiThemePreference;
  readonly initialLocale?: UiLocalePreference;
  readonly initialHat?: string;
  readonly initialMcpTokens?: readonly UiPersonalMcpTokenItem[];
  readonly initialTab?: UiUserSettingsTabKey;
  readonly activeTab?: UiUserSettingsTabKey;
  readonly onActiveTabChange?: (tab: UiUserSettingsTabKey) => void;
  readonly modalOpen?: boolean;
  readonly onModalOpenChange?: (open: boolean) => void;
  readonly labels: UserAccountDropdownAndSettingsLabels;
  readonly accountProfile?: UiUserAccountProfileView;
  readonly passthroughConnectors?: readonly UiUserPassthroughConnectorView[];
  readonly onPreferencesSync?: (patch: UserAccountPreferencesPatch) => void;
  readonly onLogout?: () => void;
  readonly onNavigateAssistantBehavior?: (redirectUri: string) => void;
  readonly onSavePassthroughToken?: (
    connectorId: string,
    externalLogin: string,
    secretValue: string,
  ) => void | Promise<void>;
  readonly onRevokePassthroughToken?: (connectorId: string) => void | Promise<void>;
}
