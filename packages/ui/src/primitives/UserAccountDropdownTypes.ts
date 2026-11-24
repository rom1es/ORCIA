/**
 * Types and interfaces for Sidebar Account Popover & 5-Tab Settings Modal (`AD-21`, `Story 20.3`).
 *
 * Isolated in `packages/ui` — zero imports of `@orcia/api-client` or `@tanstack/react-router`.
 */

import type { RgaaModalGuardLabels } from "../components/RgaaModalDialog";
import type { RoleDisplayLabels } from "./UserRoleDisplayLabels";

export type UiThemePreference = "light" | "dark" | "system";
export type UiLocalePreference = "fr" | "en";
export type UiAssistantTone = "balanced" | "concise" | "detailed";
export type UiUserSettingsTabKey =
  | "GENERAL"
  | "PERSONALIZATION"
  | "ACCOUNT_SECURITY"
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
  readonly createdAtIso?: string | null;
  readonly expiresAtIso?: string | null;
}

export interface CreateMcpTokenDraftInput {
  readonly label: string;
  readonly targetKind: UiMcpTargetKind;
  readonly targetSlug: string;
  readonly expiresInDays: 30 | 90;
  readonly rpmLimit: number;
}

export interface UserPasswordSecurityLabels {
  readonly title: string;
  readonly renewalRequiredBadge: string;
  readonly temporaryPasswordWarning: string;
  readonly currentPasswordLabel: string;
  readonly newPasswordLabel: string;
  readonly confirmPasswordLabel: string;
  readonly submitButtonLabel: string;
  readonly submittingButtonLabel: string;
  readonly updatedSuccessMessage: string;
  readonly missingCurrentPasswordError: string;
  readonly weakPasswordError: string;
  readonly unchangedPasswordError: string;
  readonly mismatchPasswordError: string;
  readonly actionNotConfiguredError: string;
  readonly genericError: string;
}

export interface SidebarAccountPopoverLabels {
  readonly triggerAriaLabel: string;
  readonly personalizationLabel: string;
  readonly profileLabel: string;
  /** @deprecated Unified under personalizationLabel (`USER24-BUG-4B`). */
  readonly settingsLabel?: string;
  readonly helpMenuLabel: string;
  readonly helpCenterLabel: string;
  readonly showcaseLabel: string;
  readonly logoutLabel: string;
}

export interface UserAccountDropdownAndSettingsLabels extends RgaaModalGuardLabels {
  readonly triggerAriaLabel: string;
  readonly popover: SidebarAccountPopoverLabels;
  readonly modalTitle: string;
  readonly closeButtonLabel: string;
  readonly tabGeneralTitle: string;
  readonly tabPersonalizationTitle: string;
  readonly tabAccountSecurityTitle: string;
  readonly tabPassthroughTitle: string;
  readonly tabMcpKeysTitle: string;
  readonly appearanceLabel: string;
  readonly themeLightLabel: string;
  readonly themeDarkLabel: string;
  readonly themeSystemLabel: string;
  readonly languageLabel: string;
  readonly localeFrLabel: string;
  readonly localeEnLabel: string;
  readonly autoOpenHelpLabel: string;
  readonly notificationsEnabledLabel: string;
  readonly assistantHatLabel: string;
  readonly assistantHatOptions: Readonly<Record<string, string>>;
  readonly assistantToneLabel: string;
  readonly assistantToneOptions: Readonly<Record<UiAssistantTone, string>>;
  readonly personalInstructionsLabel: string;
  readonly personalInstructionsPlaceholder: string;
  readonly savePersonalizationLabel: string;
  readonly personalizationSavedMessage: string;
  readonly customizeAssistantRedirectCta: string;
  readonly testPassthroughTokenCta: string;
  readonly mcpTargetKindLabel: string;
  readonly mcpTokenLabelField: string;
  readonly mcpTokenLabelPlaceholder: string;
  readonly mcpTargetSlugLabel: string;
  readonly mcpTargetSlugPlaceholder: string;
  readonly mcpExpiryLabel: string;
  readonly mcpExpiry30Label: string;
  readonly mcpExpiry90Label: string;
  readonly mcpRpmLimitLabel: string;
  readonly generateMcpTokenCta: string;
  readonly issuedPlaintextWarning: string;
  readonly copyPlaintextCta: string;
  readonly copiedPlaintextLabel: string;
  readonly revokeMcpTokenCta: string;
  readonly revokedBadgeLabel: string;
  readonly emptyMcpTokensLabel: string;
  readonly targetWholeSpaceLabel: string;
  readonly targetSingleAgentLabel: string;
  readonly ideJsonReadyTitle: string;
  readonly savingLabel: string;
  readonly preferencesSavedMessage: string;
  readonly twoFactorSectionTitle: string;
  readonly twoFactorConfiguredLabel: string;
  readonly twoFactorOptionalPolicyLabel: string;
  readonly profileIdentityTitle: string;
  readonly profileTeamsFinopsTitle: string;
  readonly profileTeamsReadOnlyBadge: string;
  readonly profileTeamsEmptyText: string;
  readonly profileBillingActiveLabel: string;
  readonly profileBillingInactiveLabel: string;
  readonly profileBillingUnitsPrefix: string;
  readonly passthroughAttributionTitle: string;
  readonly passthroughAttributionSubtitle: string;
  readonly passthroughTokenSavedMessage: string;
  readonly passthroughTokenSaveError: string;
  readonly passthroughTokenRevokedMessage: string;
  readonly passthroughTokenRevokeError: string;
  readonly passthroughNotConnectedLabel: string;
  readonly passthroughLoginPlaceholder: string;
  readonly passthroughTokenPlaceholder: string;
  readonly passthroughSaveTokenCta: string;
  readonly passthroughCancelCta: string;
  readonly passthroughNoLoginLabel: string;
  readonly passthroughReplaceTokenCta: string;
  readonly passthroughConnectTokenCta: string;
  readonly passthroughRevokeTokenCta: string;
  readonly passthroughEmptyConnectorsMessage: string;
  readonly tokenIdentifierPrefix: string;
  readonly roleDisplayLabels?: RoleDisplayLabels | Readonly<Record<string, string>>;
  readonly passwordSecurity: UserPasswordSecurityLabels;
}

export interface UserAccountPreferencesPatch {
  readonly theme?: UiThemePreference;
  readonly locale?: UiLocalePreference;
  readonly defaultAssistantHat?: string;
  readonly assistantTone?: UiAssistantTone;
  readonly personalInstructions?: string;
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
