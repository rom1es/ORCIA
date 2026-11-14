import React from "react";
import {
  RgaaDialogFooterActions,
  RgaaUnsavedChangesAlert,
  type RgaaModalDialogLabels,
} from "../components/RgaaModalDialog";
import type {
  UiLocalePreference,
  UiMcpTargetKind,
  UiPersonalMcpTokenItem,
  UiUserAccountProfileView,
  UiUserPassthroughConnectorView,
  UiUserSettingsTabKey,
  UserAccountDropdownAndSettingsLabels,
  UserAccountPreferencesPatch,
} from "./UserAccountDropdownTypes";
import { UserSettingsModalTabs } from "./UserSettingsModalTabs";

export interface UserSettingsModalDialogProps {
  readonly activeTab: UiUserSettingsTabKey;
  readonly onSelectTab: (tab: UiUserSettingsTabKey) => void;
  readonly userEmail: string;
  readonly userRole: string;
  readonly locale: UiLocalePreference;
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
  readonly guardLabels: RgaaModalDialogLabels;
  readonly showUnsavedAlert: boolean;
  readonly accountProfile?: UiUserAccountProfileView;
  readonly passthroughConnectors?: readonly UiUserPassthroughConnectorView[];
  readonly onRequestClose: () => void;
  readonly onCancelDiscard: () => void;
  readonly onConfirmDiscard: () => void;
  readonly onSaveChanges: () => void;
  readonly onChangeAutoOpenHelp: (next: boolean) => void;
  readonly onChangeNotificationsEnabled: (next: boolean) => void;
  readonly onPreferencesSync?: (patch: UserAccountPreferencesPatch) => void;
  readonly onNavigateAssistantBehavior?: (redirectUri: string) => void;
  readonly onTestPassthrough: () => void;
  readonly onSavePassthroughToken?: (
    connectorId: string,
    externalLogin: string,
    secretValue: string,
  ) => void | Promise<void>;
  readonly onRevokePassthroughToken?: (connectorId: string) => void | Promise<void>;
  readonly onChangeMcpTargetKind: (kind: UiMcpTargetKind) => void;
  readonly onChangeMcpTargetSlug: (slug: string) => void;
  readonly onChangeMcpExpiryDays: (days: 30 | 90) => void;
  readonly onChangeMcpRpmLimit: (rpm: number) => void;
  readonly onIssueMcpToken: () => void;
  readonly onRevokeMcpToken: (tokenId: string) => void;
}

export function UserSettingsModalDialog({
  activeTab,
  onSelectTab,
  userEmail,
  userRole,
  locale,
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
  guardLabels,
  showUnsavedAlert,
  accountProfile,
  passthroughConnectors,
  onRequestClose,
  onCancelDiscard,
  onConfirmDiscard,
  onSaveChanges,
  onChangeAutoOpenHelp,
  onChangeNotificationsEnabled,
  onPreferencesSync,
  onNavigateAssistantBehavior,
  onTestPassthrough,
  onSavePassthroughToken,
  onRevokePassthroughToken,
  onChangeMcpTargetKind,
  onChangeMcpTargetSlug,
  onChangeMcpExpiryDays,
  onChangeMcpRpmLimit,
  onIssueMcpToken,
  onRevokeMcpToken,
}: UserSettingsModalDialogProps): React.ReactElement {
  return (
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
            onClick={onRequestClose}
            className="px-2 py-1 rounded text-xs border border-surface-border text-text-secondary"
          >
            {locale === "en" ? "Close (Esc)" : "Fermer (Esc)"}
          </button>
        </div>

        <div className="px-4 pt-2">
          <RgaaUnsavedChangesAlert
            testIdPrefix="user-settings-modal"
            isOpen={showUnsavedAlert}
            labels={guardLabels}
            locale={locale}
            onStay={onCancelDiscard}
            onConfirmDiscard={onConfirmDiscard}
          />
        </div>

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
              onClick={() => onSelectTab(tabKey)}
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
          locale={locale}
          passthroughTested={passthroughTested}
          mcpTargetKind={mcpTargetKind}
          mcpTargetSlug={mcpTargetSlug}
          mcpExpiryDays={mcpExpiryDays}
          mcpRpmLimit={mcpRpmLimit}
          mcpTokens={mcpTokens}
          lastIssuedPlaintext={lastIssuedPlaintext}
          labels={labels}
          accountProfile={accountProfile}
          passthroughConnectors={passthroughConnectors}
          onChangeAutoOpenHelp={onChangeAutoOpenHelp}
          onChangeNotificationsEnabled={onChangeNotificationsEnabled}
          onPreferencesSync={onPreferencesSync}
          onNavigateAssistantBehavior={onNavigateAssistantBehavior}
          onTestPassthrough={onTestPassthrough}
          onSavePassthroughToken={onSavePassthroughToken}
          onRevokePassthroughToken={onRevokePassthroughToken}
          onChangeMcpTargetKind={onChangeMcpTargetKind}
          onChangeMcpTargetSlug={onChangeMcpTargetSlug}
          onChangeMcpExpiryDays={onChangeMcpExpiryDays}
          onChangeMcpRpmLimit={onChangeMcpRpmLimit}
          onIssueMcpToken={onIssueMcpToken}
          onRevokeMcpToken={onRevokeMcpToken}
        />

        <div className="px-4 py-3 border-t border-surface-border bg-surface-secondary">
          <RgaaDialogFooterActions
            testIdPrefix="user-settings-modal"
            cancelLabel={guardLabels.cancelButtonLabel}
            submitLabel={guardLabels.submitButtonLabel}
            onCancel={onRequestClose}
            onSubmit={onSaveChanges}
          />
        </div>
      </div>
    </div>
  );
}
