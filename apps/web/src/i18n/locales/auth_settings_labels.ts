import type { PlatformAuthSettingsCardLabels, SecretFieldLabels } from "@orcia/ui";

export interface AuthSettingsDictionarySection {
  readonly card: PlatformAuthSettingsCardLabels;
  readonly secretField: SecretFieldLabels;
  readonly saveSuccessMessage: string;
  readonly saveErrorMessage: string;
  readonly loadErrorMessage: string;
  readonly testOidcErrorMessage: string;
  readonly unknownErrorLabel: string;
}

export const AUTH_SETTINGS_FR_LABELS: AuthSettingsDictionarySection = {
  card: {
    heading: "Politique d'Authentification de la Plateforme",
    subtitle:
      "Choisissez un mode d'authentification exclusif (Compte local OU SSO d'organisation) et, en mode local, la politique de code de vérification à 6 chiffres.",
    authModeGroupLabel: "Mode d'authentification exclusif (/login)",
    authModeLocalTitle: "Comptes Locaux ORCIA (E-mail & Mot de passe)",
    authModeLocalDescription:
      "Les utilisateurs se connectent avec leur adresse e-mail professionnelle et leur mot de passe géré dans ORCIA. Le bouton SSO est masqué.",
    authModeSsoTitle: "SSO d'Entreprise Exclusif (OIDC)",
    authModeSsoDescription:
      "Les utilisateurs s'authentifient uniquement via votre fournisseur d'identité (OIDC). Le formulaire local et la double authentification locale sont masqués.",
    twoFactorGroupLabel: "Code de vérification à 6 chiffres (mode Local)",
    twoFactorNoneTitle: "Désactivé (mot de passe uniquement)",
    twoFactorNoneDescription:
      "Connexion en une seule étape par e-mail et mot de passe, sans code à 6 chiffres.",
    twoFactorEmailOtpTitle: "Code à 6 chiffres par E-mail (SMTP)",
    twoFactorEmailOtpDescription:
      "Après validation du mot de passe, un code unique valide 5 minutes est envoyé via le connecteur SMTP configuré.",
    twoFactorTotpTitle: "Application d'authentification (TOTP)",
    twoFactorTotpDescription:
      "Code rotatif 30s (Google Authenticator, FreeOTP…). L'enrôlement guidé s'affiche automatiquement à la première connexion.",
    smtpConfiguredBadge: "Serveur SMTP actif",
    smtpMissingBadge:
      "Aucun connecteur SMTP actif — requis avant d'activer l'envoi de codes OTP par e-mail.",
    smtpConfigureCta: "Configurer dans Connecteurs",
    oidcSectionTitle: "Paramètres OIDC du Fournisseur d'Identité",
    oidcIssuerUrlLabel: "URL Émetteur OIDC (Issuer URL)",
    oidcClientIdLabel: "Identifiant Client (Client ID)",
    oidcRedirectUriLabel: "URL de Redirection Callback",
    oidcScopesLabel: "Scopes OIDC",
    ssoButtonLabelField: "Libellé du bouton de connexion SSO",
    testOidcCta: "Tester la découverte OIDC",
    testingOidcLabel: "Test en cours...",
    oidcDiscoverySuccessPrefix: "Découverte OIDC validée",
    oidcDiscoveryFailurePrefix: "Échec découverte :",
    saveCta: "Enregistrer la politique d'authentification",
    savingLabel: "Enregistrement...",
    readOnlyNotice:
      "Seul un Administrateur de la plateforme peut modifier la politique d'authentification.",
  },
  secretField: {
    fieldLabel: "Secret Client OIDC",
    configuredBadge: "Secret configuré",
    unconfiguredBadge: "Non configuré",
    fingerprintPrefix: "Empreinte :",
    replaceSecretCta: "Remplacer le secret", // pragma: allowlist secret
    cancelReplaceCta: "Annuler",
    clearSecretCta: "Effacer le secret", // pragma: allowlist secret
    saveNewSecretCta: "Valider le secret", // pragma: allowlist secret
    inputPlaceholder: "Saisissez le client_secret OIDC...",
  },
  saveSuccessMessage: "Politique d'authentification enregistrée et appliquée immédiatement.",
  saveErrorMessage: "Impossible d'enregistrer la politique d'authentification.",
  loadErrorMessage: "Impossible de charger la configuration d'authentification.",
  testOidcErrorMessage: "Impossible de tester l'URL de découverte OIDC.",
  unknownErrorLabel: "Erreur technique inattendue.",
};

export const AUTH_SETTINGS_EN_LABELS: AuthSettingsDictionarySection = {
  card: {
    heading: "Platform Authentication Policy",
    subtitle:
      "Select one exclusive login mode (Local accounts OR Enterprise SSO) and, for local logins, whether a 6-digit verification code is required.",
    authModeGroupLabel: "Exclusive authentication mode (/login)",
    authModeLocalTitle: "ORCIA Local Accounts (Email & Password)",
    authModeLocalDescription:
      "Users sign in with their work email and ORCIA-managed password. The SSO button is hidden.",
    authModeSsoTitle: "Exclusive Enterprise SSO (OIDC)",
    authModeSsoDescription:
      "Users authenticate solely through your Identity Provider (OIDC). Local password and local 2FA forms are hidden.",
    twoFactorGroupLabel: "6-digit verification code (Local mode)",
    twoFactorNoneTitle: "Disabled (password only)",
    twoFactorNoneDescription:
      "Single-step sign-in with email and password only, with no 6-digit code prompt.",
    twoFactorEmailOtpTitle: "6-digit Email Code (SMTP)",
    twoFactorEmailOtpDescription:
      "After verifying the password, a 5-minute single-use code is emailed through the configured SMTP connector.",
    twoFactorTotpTitle: "Authenticator App (TOTP)",
    twoFactorTotpDescription:
      "Rolling 30s code (Google Authenticator, FreeOTP…). Guided enrollment opens automatically on first login.",
    smtpConfiguredBadge: "Active SMTP server",
    smtpMissingBadge:
      "No active SMTP connector — required before enabling email OTP delivery.",
    smtpConfigureCta: "Configure in Connectors",
    oidcSectionTitle: "Identity Provider (OIDC) Settings",
    oidcIssuerUrlLabel: "OIDC Issuer URL",
    oidcClientIdLabel: "Client ID",
    oidcRedirectUriLabel: "Callback Redirect URI",
    oidcScopesLabel: "OIDC Scopes",
    ssoButtonLabelField: "SSO sign-in button label",
    testOidcCta: "Test OIDC discovery",
    testingOidcLabel: "Testing...",
    oidcDiscoverySuccessPrefix: "OIDC discovery verified",
    oidcDiscoveryFailurePrefix: "Discovery failed:",
    saveCta: "Save authentication policy",
    savingLabel: "Saving...",
    readOnlyNotice: "Only a Platform Administrator can modify authentication policy.",
  },
  secretField: {
    fieldLabel: "OIDC Client Secret",
    configuredBadge: "Secret configured",
    unconfiguredBadge: "Not configured",
    fingerprintPrefix: "Fingerprint:",
    replaceSecretCta: "Replace secret", // pragma: allowlist secret
    cancelReplaceCta: "Cancel",
    clearSecretCta: "Clear secret", // pragma: allowlist secret
    saveNewSecretCta: "Apply secret", // pragma: allowlist secret
    inputPlaceholder: "Enter OIDC client_secret...",
  },
  saveSuccessMessage: "Authentication policy saved and applied immediately.",
  saveErrorMessage: "Unable to save authentication policy.",
  loadErrorMessage: "Unable to load authentication policy.",
  testOidcErrorMessage: "Unable to test OIDC discovery URL.",
  unknownErrorLabel: "Unexpected error.",
};
