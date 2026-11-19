import {
  UserSettingsModalDialog,
  type UiLocalePreference,
  type UiUserSettingsTabKey,
} from "@orcia/ui";
import React, { useEffect, useState } from "react";
import { frDictionary } from "../i18n/locales/fr";
import type { TranslationDictionary } from "../i18n/types";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { useSidebarAccountSettings } from "./useSidebarAccountSettings";

export interface ShellUserSettingsModalProps {
  readonly userEmail: string;
  readonly userRole: string;
  readonly locale: UiLocalePreference;
  readonly labels?: TranslationDictionary["userAccountAndSettings"];
  readonly onLocaleChange: (locale: UiLocalePreference) => void;
  readonly onNavigate: (href: string) => void;
}

export function ShellUserSettingsModal({
  userEmail,
  userRole,
  locale,
  labels = frDictionary.userAccountAndSettings,
  onLocaleChange,
  onNavigate,
}: ShellUserSettingsModalProps): React.ReactElement {
  const modalOpen = useAuthSessionStore((s) => s.userSettingsModalOpen);
  const modalInitialTab = useAuthSessionStore((s) => s.userSettingsModalInitialTab);
  const setModalOpen = useAuthSessionStore((s) => s.setUserSettingsModalOpen);
  const mustChangePassword = useAuthSessionStore((s) => s.mustChangePassword);

  const [activeTab, setActiveTab] = useState<UiUserSettingsTabKey>("GENERAL");

  useEffect(() => {
    if (modalInitialTab) {
      setActiveTab(modalInitialTab);
    }
  }, [modalInitialTab]);

  const settings = useSidebarAccountSettings({
    locale,
    modalOpen,
    labels,
    onLocaleChange,
  });

  return (
    <UserSettingsModalDialog
      open={modalOpen}
      onOpenChange={setModalOpen}
      activeTab={activeTab}
      onSelectTab={setActiveTab}
      userEmail={userEmail}
      userRole={userRole}
      theme={settings.theme}
      locale={locale}
      defaultAssistantHat={settings.defaultAssistantHat}
      assistantTone={settings.assistantTone}
      personalInstructions={settings.personalInstructions}
      autoOpenHelp={settings.autoOpenHelp}
      notificationsEnabled={settings.notificationsEnabled}
      twoFactorMode={settings.twoFactorMode}
      mcpTokens={settings.mcpTokens}
      lastIssuedPlaintext={settings.lastIssuedPlaintext}
      isSavingPreferences={settings.isSavingPrefs}
      preferencesError={settings.prefsError}
      preferencesSavedMessage={settings.prefsSavedMsg}
      isSubmittingMcp={settings.isSubmittingMcp}
      mcpError={settings.mcpError}
      labels={labels}
      accountProfile={settings.accountProfile}
      passthroughConnectors={settings.passthroughConnectors}
      mustChangePassword={mustChangePassword}
      onUpdatePreferences={settings.handleUpdatePreferences}
      onNavigateAssistantBehavior={(uri) => {
        setModalOpen(false);
        onNavigate(uri);
      }}
      onSavePassthroughToken={settings.handleSavePassthrough}
      onRevokePassthroughToken={settings.handleRevokePassthrough}
      onChangePassword={settings.handleChangePassword}
      onCreateMcpToken={settings.handleCreateMcpToken}
      onRevokeMcpToken={settings.handleRevokeMcpToken}
    />
  );
}
