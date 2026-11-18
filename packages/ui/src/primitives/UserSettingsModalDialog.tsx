import React, { useState } from "react";
import { OrciaIcon, type OrciaIconName } from "../components/icons";
import {
  RgaaUnsavedChangesAlert,
  resolveRgaaModalGuardLabels,
  useUnsavedChangesDialogGuard,
} from "../components/RgaaModalDialog";
import { OrciaAlertBanner } from "./DesignSystemControls";
import type {
  CreateMcpTokenDraftInput,
  UiAssistantTone,
  UiLocalePreference,
  UiPersonalMcpTokenItem,
  UiThemePreference,
  UiUserAccountProfileView,
  UiUserPassthroughConnectorView,
  UiUserSettingsTabKey,
  UserAccountDropdownAndSettingsLabels,
  UserAccountPreferencesPatch,
} from "./UserAccountDropdownTypes";
import { UserSettingsGeneralTab } from "./UserSettingsGeneralTab";
import { UserSettingsMcpTokensTab } from "./UserSettingsMcpTokensTab";
import { UserSettingsPersonalizationTab } from "./UserSettingsPersonalizationTab";
import {
  UserSettingsPassthroughTab,
  UserSettingsProfileTab,
} from "./UserSettingsProfileAndPassthroughTabs";

export interface UserSettingsModalDialogProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly activeTab: UiUserSettingsTabKey;
  readonly onSelectTab: (tab: UiUserSettingsTabKey) => void;
  readonly userEmail: string;
  readonly userRole: string;
  readonly theme: UiThemePreference;
  readonly locale: UiLocalePreference;
  readonly defaultAssistantHat: string;
  readonly assistantTone: UiAssistantTone;
  readonly personalInstructions: string;
  readonly autoOpenHelp: boolean;
  readonly notificationsEnabled: boolean;
  readonly twoFactorMode?: string;
  readonly mcpTokens: readonly UiPersonalMcpTokenItem[];
  readonly lastIssuedPlaintext: string | null;
  readonly isSavingPreferences?: boolean;
  readonly preferencesError?: string | null;
  readonly preferencesSavedMessage?: string | null;
  readonly isSubmittingMcp?: boolean;
  readonly mcpError?: string | null;
  readonly labels: UserAccountDropdownAndSettingsLabels;
  readonly accountProfile?: UiUserAccountProfileView;
  readonly passthroughConnectors?: readonly UiUserPassthroughConnectorView[];
  readonly mustChangePassword?: boolean;
  readonly onUpdatePreferences: (patch: UserAccountPreferencesPatch) => void | Promise<void>;
  readonly onNavigateAssistantBehavior?: (redirectUri: string) => void;
  readonly onSavePassthroughToken?: (
    connectorId: string,
    externalLogin: string,
    secretValue: string,
  ) => void | Promise<void>;
  readonly onRevokePassthroughToken?: (connectorId: string) => void | Promise<void>;
  readonly onChangePassword?: (
    currentPassword: string,
    newPassword: string,
  ) => Promise<{ success: boolean; error?: string } | void>;
  readonly onCreateMcpToken: (input: CreateMcpTokenDraftInput) => void | Promise<void>;
  readonly onRevokeMcpToken: (tokenId: string) => void | Promise<void>;
}

export function UserSettingsModalDialog({
  open,
  onOpenChange,
  activeTab,
  onSelectTab,
  userEmail,
  userRole,
  theme,
  locale,
  defaultAssistantHat,
  assistantTone,
  personalInstructions,
  autoOpenHelp,
  notificationsEnabled,
  twoFactorMode = "NONE",
  mcpTokens,
  lastIssuedPlaintext,
  isSavingPreferences = false,
  preferencesError = null,
  preferencesSavedMessage = null,
  isSubmittingMcp = false,
  mcpError = null,
  labels,
  accountProfile,
  passthroughConnectors,
  mustChangePassword,
  onUpdatePreferences,
  onNavigateAssistantBehavior,
  onSavePassthroughToken,
  onRevokePassthroughToken,
  onChangePassword,
  onCreateMcpToken,
  onRevokeMcpToken,
}: UserSettingsModalDialogProps): React.ReactElement | null {
  const [isDirty, setIsDirty] = useState(false);
  const guardLabels = resolveRgaaModalGuardLabels(labels, locale);

  const { showUnsavedAlert, requestClose, cancelDiscard, confirmDiscard } =
    useUnsavedChangesDialogGuard({
      isOpen: open,
      isDirty,
      onClose: () => onOpenChange(false),
      onDiscardChanges: () => setIsDirty(false),
    });

  if (!open) {
    return null;
  }

  const tabs: readonly {
    readonly key: UiUserSettingsTabKey;
    readonly label: string;
    readonly icon: OrciaIconName;
  }[] = [
    { key: "GENERAL", label: labels.tabGeneralTitle, icon: "configuration" },
    { key: "PERSONALIZATION", label: labels.tabPersonalizationTitle, icon: "sparkles" },
    { key: "ACCOUNT_SECURITY", label: labels.tabAccountSecurityTitle, icon: "shield" },
    { key: "PASSTHROUGH_SOURCES", label: labels.tabPassthroughTitle, icon: "plug" },
    { key: "IDE_MCP_KEYS", label: labels.tabMcpKeysTitle, icon: "keyLock" },
  ];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={labels.modalTitle}
      data-testid="user-settings-modal"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: "var(--color-modal-backdrop)" }}
    >
      <div
        className="flex h-[580px] w-full max-w-[820px] flex-col overflow-hidden rounded-xl border shadow-2xl"
        style={{
          backgroundColor: "var(--color-bg-surface)",
          borderColor: "var(--color-border-subtle)",
          color: "var(--color-text-primary)",
        }}
      >
        <div
          className="flex items-center justify-between border-b px-4 py-3"
          style={{ borderColor: "var(--color-border-subtle)" }}
        >
          <h2 className="text-sm font-semibold">{labels.modalTitle}</h2>
          <button
            type="button"
            data-testid="user-settings-modal-close-btn"
            onClick={requestClose}
            className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
          >
            <OrciaIcon name="close" size={14} />
            <span>{labels.closeButtonLabel}</span>
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
          {preferencesError && (
            <OrciaAlertBanner tone="crimson" testId="user-settings-modal-error-banner">
              {preferencesError}
            </OrciaAlertBanner>
          )}
        </div>

        <div className="flex min-h-0 flex-1">
          <nav
            role="tablist"
            aria-orientation="vertical"
            data-testid="user-settings-tabs"
            className="flex w-52 shrink-0 flex-col gap-1 border-r p-3"
            style={{
              borderColor: "var(--color-border-subtle)",
              backgroundColor: "var(--color-bg-elevated)",
            }}
          >
            {tabs.map((tab) => {
              const selected = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  data-testid={`user-settings-tab-${tab.key}`}
                  data-active={selected ? "true" : "false"}
                  onClick={() => onSelectTab(tab.key)}
                  className="orcia-sidebar-nav-btn gap-2 px-2.5 py-2 text-left text-xs"
                >
                  <OrciaIcon name={tab.icon} size={15} />
                  <span className="truncate">{tab.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="flex-1 overflow-y-auto p-4 text-xs">
            {activeTab === "GENERAL" && (
              <UserSettingsGeneralTab
                theme={theme}
                locale={locale}
                autoOpenHelp={autoOpenHelp}
                notificationsEnabled={notificationsEnabled}
                labels={labels}
                onUpdatePreferences={onUpdatePreferences}
              />
            )}

            {activeTab === "PERSONALIZATION" && (
              <UserSettingsPersonalizationTab
                defaultAssistantHat={defaultAssistantHat}
                assistantTone={assistantTone}
                personalInstructions={personalInstructions}
                labels={labels}
                isSaving={isSavingPreferences}
                savedMessage={preferencesSavedMessage}
                onUpdatePreferences={onUpdatePreferences}
                onDirtyChange={setIsDirty}
                onNavigateAssistantBehavior={onNavigateAssistantBehavior}
              />
            )}

            {activeTab === "ACCOUNT_SECURITY" && (
              <UserSettingsProfileTab
                userEmail={userEmail}
                userRole={userRole}
                locale={locale}
                accountProfile={accountProfile}
                mustChangePassword={mustChangePassword}
                twoFactorMode={twoFactorMode}
                onChangePassword={onChangePassword}
                labels={labels}
                passwordSecurity={labels.passwordSecurity}
              />
            )}

            {activeTab === "PASSTHROUGH_SOURCES" && (
              <UserSettingsPassthroughTab
                labels={labels}
                passthroughConnectors={passthroughConnectors}
                onSavePassthroughToken={onSavePassthroughToken}
                onRevokePassthroughToken={onRevokePassthroughToken}
              />
            )}

            {activeTab === "IDE_MCP_KEYS" && (
              <UserSettingsMcpTokensTab
                mcpTokens={mcpTokens}
                lastIssuedPlaintext={lastIssuedPlaintext}
                isSubmitting={isSubmittingMcp}
                errorMessage={mcpError}
                labels={labels}
                onCreateMcpToken={onCreateMcpToken}
                onRevokeMcpToken={onRevokeMcpToken}
                onDirtyChange={setIsDirty}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
