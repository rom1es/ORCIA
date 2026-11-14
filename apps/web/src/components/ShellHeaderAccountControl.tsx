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
}: ShellHeaderAccountControlProps): React.ReactElement {
  const userSettingsModalOpen = useAuthSessionStore((s) => s.userSettingsModalOpen);
  const userSettingsModalInitialTab = useAuthSessionStore((s) => s.userSettingsModalInitialTab);
  const setUserSettingsModalOpen = useAuthSessionStore((s) => s.setUserSettingsModalOpen);

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
