import {
  UserAccountDropdownAndSettingsModal,
  type UiLocalePreference,
  type UiUserAccountProfileView,
  type UiUserPassthroughConnectorView,
  type UiUserSettingsTabKey,
} from "@orcia/ui";
import React, { useCallback, useEffect, useState } from "react";
import { createOrciaApiClient } from "@orcia/api-client";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { frDictionary } from "../i18n/locales/fr";
import type { TranslationDictionary } from "../i18n/types";

export interface ShellHeaderAccountControlProps {
  readonly userDisplayName?: string;
  readonly userEmail?: string;
  readonly userRole?: string;
  readonly activeHat?: string;
  readonly locale?: UiLocalePreference;
  readonly labels?: TranslationDictionary["userAccountAndSettings"];
  readonly onLocaleChange?: (locale: UiLocalePreference) => void;
  readonly onActiveHatChange?: (hat: string) => void;
  readonly onNavigateAssistantBehavior?: (uri: string) => void;
  readonly onLogout?: () => void;
  readonly onChangePassword?: (
    currentPassword: string,
    newPassword: string,
  ) => Promise<{ success: boolean; error?: string } | void>;
}

export function ShellHeaderAccountControl({
  userDisplayName = "Utilisateur",
  userEmail = "user@orcia.local",
  userRole = "PLATFORM_ADMIN",
  activeHat = "PLATFORM_ADMIN",
  locale = "fr",
  labels = frDictionary.userAccountAndSettings,
  onLocaleChange,
  onActiveHatChange,
  onNavigateAssistantBehavior,
  onLogout,
  onChangePassword,
}: ShellHeaderAccountControlProps): React.ReactElement {
  const userSettingsModalOpen = useAuthSessionStore((s) => s.userSettingsModalOpen);
  const userSettingsModalInitialTab = useAuthSessionStore((s) => s.userSettingsModalInitialTab);
  const setUserSettingsModalOpen = useAuthSessionStore((s) => s.setUserSettingsModalOpen);
  const mustChangePassword = useAuthSessionStore((s) => s.mustChangePassword);
  const clearMustChangePassword = useAuthSessionStore((s) => s.clearMustChangePassword);
  const logoutSession = useAuthSessionStore((s) => s.logoutSession);

  const [accountProfile, setAccountProfile] = useState<UiUserAccountProfileView | undefined>(undefined);
  const [passthroughConnectors, setPassthroughConnectors] = useState<
    readonly UiUserPassthroughConnectorView[] | undefined
  >(undefined);

  const client = createOrciaApiClient({ baseUrl: "" });

  const loadData = useCallback(async () => {
    try {
      const [profRes, connRes] = await Promise.all([
        client.getUserAccountProfile(),
        client.listUserPassthroughTokens(),
      ]);
      setAccountProfile({
        principalId: profRes.principal_id,
        displayName: profRes.display_name,
        email: profRes.email,
        roles: profRes.roles,
        teams: profRes.teams.map((t) => ({
          id: t.id,
          slug: t.slug,
          name: t.name,
          unitType: t.unit_type,
          billingEnabled: t.billing_enabled,
          isLead: t.is_lead,
        })),
        billingOrgUnits: profRes.billing_org_units.map((b) => ({
          id: b.id,
          slug: b.slug,
          name: b.name,
          unitType: b.unit_type,
          billingEnabled: b.billing_enabled,
          isLead: b.is_lead,
        })),
      });

      setPassthroughConnectors(
        connRes.items.map((c) => ({
          connectorId: c.connector_id,
          connectorName: c.connector_name,
          connectorKind: c.connector_kind,
          baseUrl: c.base_url,
          authMode: c.auth_mode,
          connected: c.connected,
          externalAuthorLogin: c.external_author_login,
          secretStatus: {
            configured: c.secret_status.configured,
            fingerprint: c.secret_status.fingerprint,
            updatedAtIso: c.secret_status.updated_at_iso,
          },
        })),
      );
    } catch {
      // Graceful fallback if network unavailable in unit mock tests
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (userSettingsModalOpen) {
      void loadData();
    }
  }, [userSettingsModalOpen, loadData]);

  const handleSavePassthrough = async (
    connectorId: string,
    externalLogin: string,
    secretValue: string,
  ) => {
    await client.upsertUserPassthroughToken(connectorId, {
      external_author_login: externalLogin,
      secret_value: secretValue,
    });
    await loadData();
  };

  const handleRevokePassthrough = async (connectorId: string) => {
    await client.revokeUserPassthroughToken(connectorId);
    await loadData();
  };

  const handleLogout = async () => {
    await logoutSession();
    if (onLogout) {
      onLogout();
    } else if (typeof window !== "undefined") {
      window.location.assign("/login");
    }
  };

  const handleChangePassword = async (currentPassword: string, newPassword: string) => {
    if (onChangePassword) {
      return onChangePassword(currentPassword, newPassword);
    }
    try {
      await client.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      clearMustChangePassword();
      return { success: true };
    } catch (err: unknown) {
      return {
        success: false,
        error: err instanceof Error ? err.message : "Erreur de modification du mot de passe",
      };
    }
  };

  return (
    <UserAccountDropdownAndSettingsModal
      userDisplayName={userDisplayName}
      userEmail={userEmail}
      userRole={userRole}
      initialHat={activeHat}
      initialLocale={locale}
      initialTab={userSettingsModalInitialTab as UiUserSettingsTabKey | undefined}
      modalOpen={userSettingsModalOpen}
      onModalOpenChange={setUserSettingsModalOpen}
      labels={labels}
      accountProfile={accountProfile}
      passthroughConnectors={passthroughConnectors}
      mustChangePassword={mustChangePassword}
      onChangePassword={handleChangePassword}
      onLogout={handleLogout}
      onSavePassthroughToken={handleSavePassthrough}
      onRevokePassthroughToken={handleRevokePassthrough}
      onPreferencesSync={(patch) => {
        if (patch.locale && patch.locale !== locale) {
          onLocaleChange?.(patch.locale);
        }
        if (patch.defaultHat && patch.defaultHat !== activeHat) {
          onActiveHatChange?.(patch.defaultHat);
        }
      }}
      onNavigateAssistantBehavior={onNavigateAssistantBehavior}
    />
  );
}
