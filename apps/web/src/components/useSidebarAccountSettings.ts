import { createOrciaApiClient } from "@orcia/api-client";
import type {
  CreateMcpTokenDraftInput,
  UiAssistantTone,
  UiLocalePreference,
  UiPersonalMcpTokenItem,
  UiThemePreference,
  UiUserAccountProfileView,
  UiUserPassthroughConnectorView,
  UiUserSettingsTabKey,
  UserAccountPreferencesPatch,
} from "@orcia/ui";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  readSavedAssistantGovernancePrefs,
  writeSavedAssistantGovernancePrefs,
} from "../features/inbox/assistantFoldersAndPrefsStore";
import type { TranslationDictionary } from "../i18n/types";
import { useAuthSessionStore } from "../stores/authSessionStore";
import {
  applyZeroMsDomPreferences,
  extractUiErrorMessage,
  mapAccountProfileDto,
  mapMcpTokensDto,
  mapPassthroughConnectorsDto,
} from "./sidebarAccountMappers";

export function useSidebarAccountSettings(options: {
  readonly locale: UiLocalePreference;
  readonly modalOpen: boolean;
  readonly activeTab?: UiUserSettingsTabKey;
  readonly labels: TranslationDictionary["userAccountAndSettings"];
  readonly onLocaleChange: (locale: UiLocalePreference) => void;
}) {
  const { locale, modalOpen, activeTab = "GENERAL", labels, onLocaleChange } = options;
  const clearMustChangePassword = useAuthSessionStore((s) => s.clearMustChangePassword);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);

  const [theme, setTheme] = useState<UiThemePreference>("light");
  const [defaultAssistantHat, setDefaultAssistantHat] = useState<string>("ANALYST_PM_PO");
  const [assistantTone, setAssistantTone] = useState<UiAssistantTone>("balanced");
  const [personalInstructions, setPersonalInstructions] = useState<string>("");
  const [autoOpenHelp, setAutoOpenHelp] = useState<boolean>(true);
  const [notificationsEnabled, setNotificationsEnabled] = useState<boolean>(true);
  const [twoFactorMode, setTwoFactorMode] = useState<string>("NONE");
  const [accountProfile, setAccountProfile] = useState<UiUserAccountProfileView | undefined>(undefined);
  const [passthroughConnectors, setPassthroughConnectors] = useState<
    readonly UiUserPassthroughConnectorView[] | undefined
  >(undefined);
  const [mcpTokens, setMcpTokens] = useState<readonly UiPersonalMcpTokenItem[]>([]);
  const [lastIssuedPlaintext, setLastIssuedPlaintext] = useState<string | null>(null);
  const [isSavingPrefs, setIsSavingPrefs] = useState<boolean>(false);
  const [prefsError, setPrefsError] = useState<string | null>(null);
  const [prefsSavedMsg, setPrefsSavedMsg] = useState<string | null>(null);
  const [isSubmittingMcp, setIsSubmittingMcp] = useState<boolean>(false);
  const [mcpError, setMcpError] = useState<string | null>(null);

  const client = useMemo(
    () =>
      createOrciaApiClient({
        baseUrl: "",
        locale,
        ...(readOnlyObserver
          ? { extraHeaders: { "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER" } }
          : {}),
      }),
    [locale, readOnlyObserver],
  );

  const loadPreferences = useCallback(async () => {
    try {
      const prefs = await client.getUserPreferences();
      if (!prefs || typeof prefs !== "object") return;
      const validTheme: UiThemePreference =
        prefs.theme === "dark" || prefs.theme === "system" || prefs.theme === "light"
          ? prefs.theme
          : "light";
      const validLocale: UiLocalePreference | null =
        prefs.locale === "fr" || prefs.locale === "en" ? prefs.locale : null;
      const validTone: UiAssistantTone =
        prefs.assistant_tone === "concise" ||
        prefs.assistant_tone === "detailed" ||
        prefs.assistant_tone === "balanced"
          ? prefs.assistant_tone
          : "balanced";
      const nextHat =
        typeof prefs.default_assistant_hat === "string" && prefs.default_assistant_hat.trim()
          ? prefs.default_assistant_hat
          : typeof prefs.default_hat === "string" && prefs.default_hat.trim()
            ? prefs.default_hat
            : "ANALYST_PM_PO";

      setTheme(validTheme);
      setDefaultAssistantHat(nextHat);
      setAssistantTone(validTone);
      setPersonalInstructions(
        typeof prefs.personal_instructions === "string" ? prefs.personal_instructions : "",
      );
      if (typeof prefs.auto_open_contextual_help === "boolean") {
        setAutoOpenHelp(prefs.auto_open_contextual_help);
      }
      if (typeof prefs.notifications_enabled === "boolean") {
        setNotificationsEnabled(prefs.notifications_enabled);
      }
      if (validLocale) {
        applyZeroMsDomPreferences(validTheme, validLocale);
        if (validLocale !== locale) {
          onLocaleChange(validLocale);
        }
      }
      const currentAst = readSavedAssistantGovernancePrefs();
      writeSavedAssistantGovernancePrefs({
        ...currentAst,
        defaultHat: nextHat,
        personalInstructions:
          typeof prefs.personal_instructions === "string" && prefs.personal_instructions
            ? prefs.personal_instructions
            : currentAst.personalInstructions,
      });
    } catch (err: unknown) {
      setPrefsError(extractUiErrorMessage(err, labels.savingLabel));
    }
  }, [client, labels.savingLabel, locale, onLocaleChange]);

  const loadModalDetails = useCallback(async () => {
    try {
      const [profRes, connRes, tokensRes, authCfgRes] = await Promise.all([
        client.getUserAccountProfile(),
        client.listUserPassthroughTokens(),
        client.listMcpTokens(),
        client.getPublicAuthConfig(),
      ]);
      setAccountProfile(mapAccountProfileDto(profRes));
      setPassthroughConnectors(mapPassthroughConnectorsDto(connRes.items));
      setMcpTokens(mapMcpTokensDto(tokensRes.tokens));
      if (authCfgRes?.two_factor_mode) {
        setTwoFactorMode(authCfgRes.two_factor_mode);
      }
    } catch (err: unknown) {
      setPrefsError(extractUiErrorMessage(err, labels.passwordSecurity?.genericError ?? "Error"));
    }
  }, [client, labels.passwordSecurity?.genericError]);

  const isHydrating = useAuthSessionStore((s) => s.isHydrating);
  const isAuthenticated = useAuthSessionStore((s) => s.isAuthenticated);

  useEffect(() => {
    if (isHydrating || !isAuthenticated) return;
    void loadPreferences();
  }, [isHydrating, isAuthenticated, loadPreferences]);

  useEffect(() => {
    if (!modalOpen || activeTab !== "IDE_MCP_KEYS") setLastIssuedPlaintext(null);
  }, [modalOpen, activeTab]);

  useEffect(() => {
    if (modalOpen && !isHydrating && isAuthenticated) {
      setPrefsError(null);
      setMcpError(null);
      void loadPreferences();
      void loadModalDetails();
    }
  }, [modalOpen, isHydrating, isAuthenticated, loadPreferences, loadModalDetails]);

  const handleUpdatePreferences = async (patch: UserAccountPreferencesPatch): Promise<void> => {
    setIsSavingPrefs(true);
    setPrefsError(null);
    setPrefsSavedMsg(null);
    try {
      const updated = await client.updateUserPreferences({
        theme: patch.theme,
        locale: patch.locale,
        default_assistant_hat: patch.defaultAssistantHat,
        default_hat: patch.defaultAssistantHat,
        assistant_tone: patch.assistantTone,
        personal_instructions: patch.personalInstructions,
        auto_open_contextual_help: patch.autoOpenContextualHelp,
        notifications_enabled: patch.notificationsEnabled,
      });
      setTheme(updated.theme);
      setDefaultAssistantHat(updated.default_assistant_hat);
      setAssistantTone(updated.assistant_tone);
      setPersonalInstructions(updated.personal_instructions);
      setAutoOpenHelp(updated.auto_open_contextual_help);
      setNotificationsEnabled(updated.notifications_enabled);
      if (updated.locale === "fr" || updated.locale === "en") {
        applyZeroMsDomPreferences(updated.theme, updated.locale);
        if (updated.locale !== locale) {
          onLocaleChange(updated.locale);
        }
      }
      const currentAst = readSavedAssistantGovernancePrefs();
      writeSavedAssistantGovernancePrefs({
        ...currentAst,
        defaultHat: updated.default_assistant_hat,
        personalInstructions: updated.personal_instructions || currentAst.personalInstructions,
      });
      setPrefsSavedMsg(labels.preferencesSavedMessage);
    } catch (err: unknown) {
      setPrefsError(extractUiErrorMessage(err, labels.passwordSecurity?.genericError ?? "Error"));
    } finally {
      setIsSavingPrefs(false);
    }
  };

  const handleCreateMcpToken = async (input: CreateMcpTokenDraftInput): Promise<void> => {
    setIsSubmittingMcp(true);
    setMcpError(null);
    try {
      const effectiveSlug = input.targetSlug.trim() || "scope-global";
      const issued = await client.createMcpToken({
        label: input.label,
        expires_in_days: input.expiresInDays,
        rpm_limit: input.rpmLimit,
        allowed_workspace_slugs: [effectiveSlug],
        exposed_capabilities: ["ASSISTANT", "KB_GLOSSARY_SEARCH"],
        target_kind: input.targetKind,
        target_slug: effectiveSlug,
      });
      // Refresh token list before revealing plaintext so form dirty state resets atomically.
      await loadModalDetails();
      setLastIssuedPlaintext(issued.plaintext_token);
    } catch (err: unknown) {
      setMcpError(extractUiErrorMessage(err, labels.passwordSecurity?.genericError ?? "Error"));
    } finally {
      setIsSubmittingMcp(false);
    }
  };

  const handleRevokeMcpToken = async (tokenId: string): Promise<void> => {
    setMcpError(null);
    try {
      await client.revokeMcpToken(tokenId);
      await loadModalDetails();
    } catch (err: unknown) {
      setMcpError(extractUiErrorMessage(err, labels.passwordSecurity?.genericError ?? "Error"));
    }
  };

  const handleSavePassthrough = async (
    connectorId: string,
    externalLogin: string,
    secretValue: string,
  ): Promise<void> => {
    await client.upsertUserPassthroughToken(connectorId, {
      external_author_login: externalLogin,
      secret_value: secretValue,
    });
    await loadModalDetails();
  };

  const handleRevokePassthrough = async (connectorId: string): Promise<void> => {
    await client.revokeUserPassthroughToken(connectorId);
    await loadModalDetails();
  };

  const handleChangePassword = async (currentPassword: string, newPassword: string) => {
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
        error: extractUiErrorMessage(err, labels.passwordSecurity?.genericError ?? "Error"),
      };
    }
  };

  return {
    theme,
    defaultAssistantHat,
    assistantTone,
    personalInstructions,
    autoOpenHelp,
    notificationsEnabled,
    twoFactorMode,
    accountProfile,
    passthroughConnectors,
    mcpTokens,
    lastIssuedPlaintext,
    isSavingPrefs,
    prefsError,
    prefsSavedMsg,
    isSubmittingMcp,
    mcpError,
    handleUpdatePreferences,
    handleCreateMcpToken,
    handleRevokeMcpToken,
    handleSavePassthrough,
    handleRevokePassthrough,
    handleChangePassword,
  };
}
