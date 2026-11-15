import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import {
  OrciaAlertBanner,
  PlatformAuthSettingsCard,
  type PlatformAuthSettingsDraft,
  type SecretFieldLabels,
} from "../index";

const MOCK_LABELS = {
  heading: "Authentification de la Plateforme",
  subtitle: "Configurez les modes de connexion et le deuxième facteur.",
  authModeGroupLabel: "Mode d'authentification principal",
  authModeLocalTitle: "Mode Local",
  authModeLocalDescription: "Comptes internes avec mot de passe.",
  authModeSsoTitle: "Mode SSO / OIDC",
  authModeSsoDescription: "Fédération d'identité d'entreprise.",
  twoFactorGroupLabel: "Code de vérification à 6 chiffres (mode Local)",
  twoFactorNoneTitle: "Désactivé",
  twoFactorNoneDescription: "Authentification à facteur unique.",
  twoFactorEmailOtpTitle: "OTP par E-mail",
  twoFactorEmailOtpDescription: "Code à 6 chiffres envoyé par courriel.",
  twoFactorTotpTitle: "Application TOTP",
  twoFactorTotpDescription: "Google Authenticator ou compatible.",
  smtpConfiguredBadge: "Serveur SMTP opérationnel",
  smtpMissingBadge: "Connecteur SMTP requis pour l'envoi d'e-mails OTP",
  smtpConfigureCta: "Configurer le connecteur SMTP",
  oidcSectionTitle: "Configuration du fournisseur OIDC d'Entreprise",
  oidcIssuerUrlLabel: "URL de l'émetteur (Issuer)",
  oidcClientIdLabel: "Identifiant Client (Client ID)",
  oidcRedirectUriLabel: "URI de redirection",
  oidcScopesLabel: "Portées (Scopes)",
  ssoButtonLabelField: "Libellé du bouton SSO",
  testOidcCta: "Tester la découverte OIDC",
  testingOidcLabel: "Test en cours...",
  oidcDiscoverySuccessPrefix: "Configuration OIDC valide",
  oidcDiscoveryFailurePrefix: "Échec de découverte OIDC",
  saveCta: "Enregistrer la politique",
  savingLabel: "Enregistrement...",
  readOnlyNotice: "Mode consultation uniquement.",
};

const MOCK_SECRET_LABELS: SecretFieldLabels = {
  fieldLabel: "Secret client",
  configuredBadge: "Secret configuré",
  unconfiguredBadge: "Secret non configuré",
  fingerprintPrefix: "Empreinte",
  replaceSecretCta: "Remplacer", // pragma: allowlist secret
  cancelReplaceCta: "Annuler",
  clearSecretCta: "Supprimer", // pragma: allowlist secret
  saveNewSecretCta: "Appliquer le secret", // pragma: allowlist secret
  inputPlaceholder: "Nouveau secret",
};

const BASE_DRAFT: PlatformAuthSettingsDraft = {
  authMode: "LOCAL",
  twoFactorMode: "EMAIL_OTP",
  oidcIssuerUrl: "",
  oidcClientId: "",
  oidcRedirectUri: "",
  oidcScopes: "openid profile email",
  ssoButtonLabel: "",
  oidcClientSecretStatus: {
    configured: false,
    fingerprint: null,
    updatedAt: "",
    updatedBy: "",
  },
  oidcClientSecretInput: { action: "keep" },
  smtpConnectorConfigured: false,
  smtpConnectorName: null,
};

describe("OrciaAlertBanner & PlatformAuthSettingsCard Spacing (@orcia/ui)", () => {
  it("renders 4 semantic tones with automatic icons and accessible ARIA roles", () => {
    const { rerender } = render(
      <OrciaAlertBanner tone="emerald" testId="alert-emerald">
        Opération réussie avec succès.
      </OrciaAlertBanner>,
    );
    const emeraldEl = screen.getByTestId("alert-emerald");
    expect(emeraldEl.getAttribute("role")).toBe("status");
    expect(emeraldEl.className).toContain("orcia-ds-alert-success");
    expect(emeraldEl.textContent).toContain("Opération réussie avec succès.");

    rerender(
      <OrciaAlertBanner tone="amber" testId="alert-amber">
        Attention requise.
      </OrciaAlertBanner>,
    );
    const amberEl = screen.getByTestId("alert-amber");
    expect(amberEl.getAttribute("role")).toBe("status");
    expect(amberEl.className).toContain("orcia-ds-alert-warning");

    rerender(
      <OrciaAlertBanner tone="crimson" testId="alert-crimson">
        Erreur critique bloquante.
      </OrciaAlertBanner>,
    );
    const crimsonEl = screen.getByTestId("alert-crimson");
    expect(crimsonEl.getAttribute("role")).toBe("alert");
    expect(crimsonEl.className).toContain("orcia-ds-alert-error");

    rerender(
      <OrciaAlertBanner tone="cobalt" testId="alert-cobalt">
        Information générale.
      </OrciaAlertBanner>,
    );
    const cobaltEl = screen.getByTestId("alert-cobalt");
    expect(cobaltEl.getAttribute("role")).toBe("status");
    expect(cobaltEl.className).toContain("orcia-ds-alert-info");
  });

  it("supports title, code, action slot and hideIcon prop", () => {
    const onAction = vi.fn();
    render(
      <OrciaAlertBanner
        tone="crimson"
        title="Erreur d'authentification"
        code="ERR_AUTH_REQUIRED"
        testId="banner-with-action"
        action={<button onClick={onAction}>Réessayer</button>}
      >
        Veuillez vous reconnecter pour poursuivre.
      </OrciaAlertBanner>,
    );

    const banner = screen.getByTestId("banner-with-action");
    expect(banner.textContent).toContain("Erreur d'authentification");
    expect(banner.textContent).toContain("ERR_AUTH_REQUIRED");
    expect(banner.textContent).toContain("Veuillez vous reconnecter pour poursuivre.");

    fireEvent.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(onAction).toHaveBeenCalledTimes(1);
  });

  it("renders PlatformAuthSettingsCard with Direction C spacing classes and unified alert banners", () => {
    const onNavigateToConnectors = vi.fn();
    render(
      <PlatformAuthSettingsCard
        value={BASE_DRAFT}
        labels={MOCK_LABELS}
        secretFieldLabels={MOCK_SECRET_LABELS}
        saveFeedback={{ kind: "error", message: "Le secret client est requis en mode SSO." }}
        onChange={() => {}}
        onSave={() => {}}
        onTestOidc={() => {}}
        onNavigateToConnectors={onNavigateToConnectors}
      />,
    );

    const section = screen.getByTestId("settings-authentication-section");
    expect(section.className).toContain("space-y-6");

    const twoFactorContainer = screen.getByTestId("auth-local-2fa-config");
    expect(twoFactorContainer.className).toContain("mt-6");
    expect(twoFactorContainer.className).toContain("pt-5");
    expect(twoFactorContainer.className).toContain("border-t");

    // Unified SMTP alert banner with status role
    const smtpBanner = screen.getByTestId("auth-smtp-status-badge");
    expect(smtpBanner.getAttribute("role")).toBe("status");
    expect(smtpBanner.className).toContain("orcia-ds-alert-warning");
    expect(smtpBanner.textContent).toContain(MOCK_LABELS.smtpMissingBadge);

    // Click SMTP CTA inside action slot
    const gotoConnectorsBtn = screen.getByTestId("auth-goto-connectors-btn");
    fireEvent.click(gotoConnectorsBtn);
    expect(onNavigateToConnectors).toHaveBeenCalledTimes(1);

    // Unified save feedback banner
    const saveFeedback = screen.getByTestId("auth-save-feedback");
    expect(saveFeedback.getAttribute("role")).toBe("alert");
    expect(saveFeedback.className).toContain("orcia-ds-alert-error");
    expect(saveFeedback.textContent).toContain("Le secret client est requis en mode SSO.");
  });
});
