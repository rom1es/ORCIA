import type {
  RoleDisplayLabels,
  TemporaryPasswordInvitationModalLabels,
} from "@orcia/ui";

export const ROLE_DISPLAY_LABELS_FR: RoleDisplayLabels = {
  platformAdmin: "Administrateur de la plateforme",
  secops: "Responsable Sécurité & Habilitations",
  buLead: "Responsable de Direction (BU)",
  teamLead: "Responsable d'Équipe",
  ontologyLead: "Référent Glossaire",
  contributor: "Contributeur",
  observer: "Observateur (Lecture seule)",
  analystPmPo: "Product Manager / Métier",
  architect: "Architecte",
  techLeadDev: "Référent Technique / Développeur",
  securityCompliance: "Sécurité & Conformité",
};

export const ROLE_DISPLAY_LABELS_EN: RoleDisplayLabels = {
  platformAdmin: "Platform Administrator",
  secops: "Security & Access Officer",
  buLead: "Business Unit Lead",
  teamLead: "Team Lead",
  ontologyLead: "Glossary Lead",
  contributor: "Contributor",
  observer: "Observer (Read-only)",
  analystPmPo: "Product Manager / Business",
  architect: "Architect",
  techLeadDev: "Technical Lead / Developer",
  securityCompliance: "Security & Compliance",
};

export const TEMP_PASSWORD_MODAL_FR: TemporaryPasswordInvitationModalLabels = {
  modalTitle: "Accès & Mot de Passe Temporaire",
  closeLabel: "Fermer",
  securityPolicyHint:
    "Ce mot de passe temporaire à usage unique est généré selon les exigences de sécurité (12 caractères, Maj/Min/Chiffre).",
  generatedPasswordTitle: "Mot de passe temporaire généré", // pragma: allowlist secret
  regeneratingLabel: "Génération...",
  regenerateLabel: "Régénérer",
  copiedCodeLabel: "Copié !",
  copyCodeLabel: "Copier le code",
  invitationMessageLabel: "Message d'invitation prêt à envoyer",
  copiedMessageLabel: "Message copié !",
  copyMessageLabel: "Copier le message d'invitation",
  clipboardBlockedError: "Copie automatique bloquée par le navigateur.",
  invitationMessageTemplate:
    "Bonjour {displayName},\n\nVoici vos accès à ORCIA :\n- Identifiant : {email}\n- Mot de passe temporaire : {temporaryPassword}\n\nConnectez-vous sur {orciaUrl}\nN'oubliez pas de changer votre mot de passe dès votre première connexion.", // pragma: allowlist secret
};

export const TEMP_PASSWORD_MODAL_EN: TemporaryPasswordInvitationModalLabels = {
  modalTitle: "Access & Temporary Password",
  closeLabel: "Close",
  securityPolicyHint:
    "This one-time temporary password complies with security policy (12 chars, upper/lower/digit).",
  generatedPasswordTitle: "Generated temporary password", // pragma: allowlist secret
  regeneratingLabel: "Regenerating...",
  regenerateLabel: "Regenerate",
  copiedCodeLabel: "Copied!",
  copyCodeLabel: "Copy code",
  invitationMessageLabel: "Invitation message ready to share",
  copiedMessageLabel: "Message copied!",
  copyMessageLabel: "Copy invitation message",
  clipboardBlockedError: "Clipboard access blocked by browser.",
  invitationMessageTemplate:
    "Hello {displayName},\n\nHere are your ORCIA access credentials:\n- Identifier: {email}\n- Temporary password: {temporaryPassword}\n\nSign in at {orciaUrl}\nPlease remember to change your password upon your first login.", // pragma: allowlist secret
};
