export interface RgaaModalGuardLabels {
  readonly cancelButtonLabel?: string;
  readonly submitButtonLabel?: string;
  readonly closeButtonLabel?: string;
  readonly cancelCta?: string;
  readonly submitCta?: string;
  readonly unsavedAlertTitle?: string;
  readonly unsavedAlertMessage?: string;
  readonly unsavedStayCta?: string;
  readonly unsavedDiscardCta?: string;
}

export type RgaaModalDialogLabels = Required<RgaaModalGuardLabels>;

export const DEFAULT_RGAA_MODAL_GUARD_LABELS_FR: Required<RgaaModalGuardLabels> = {
  cancelButtonLabel: "Annuler",
  submitButtonLabel: "Valider",
  closeButtonLabel: "Fermer",
  cancelCta: "Annuler",
  submitCta: "Valider",
  unsavedAlertTitle: "Modifications non enregistrées",
  unsavedAlertMessage:
    "Vous avez des modifications non enregistrées. Confirmer la sortie entraînera la perte de vos modifications.",
  unsavedStayCta: "Continuer l'édition",
  unsavedDiscardCta: "Quitter sans enregistrer",
};

export const DEFAULT_RGAA_MODAL_GUARD_LABELS_EN: Required<RgaaModalGuardLabels> = {
  cancelButtonLabel: "Cancel",
  submitButtonLabel: "Validate",
  closeButtonLabel: "Close",
  cancelCta: "Cancel",
  submitCta: "Validate",
  unsavedAlertTitle: "Unsaved changes",
  unsavedAlertMessage:
    "You have unsaved changes. Leaving now will discard your modifications.",
  unsavedStayCta: "Keep editing",
  unsavedDiscardCta: "Discard changes and leave",
};

export const DEFAULT_RGAA_MODAL_LABELS_FR = DEFAULT_RGAA_MODAL_GUARD_LABELS_FR;
export const DEFAULT_RGAA_MODAL_LABELS_EN = DEFAULT_RGAA_MODAL_GUARD_LABELS_EN;

const DEFAULT_RGAA_LABELS_BY_LOCALE = {
  fr: DEFAULT_RGAA_MODAL_GUARD_LABELS_FR,
  en: DEFAULT_RGAA_MODAL_GUARD_LABELS_EN,
} as const;

export function resolveRgaaModalGuardLabels(
  labels?: RgaaModalGuardLabels,
  locale: "fr" | "en" = "fr",
): Required<RgaaModalGuardLabels> {
  const defaults = DEFAULT_RGAA_LABELS_BY_LOCALE[locale];
  const cancelText =
    labels?.cancelButtonLabel ?? labels?.cancelCta ?? defaults.cancelButtonLabel;
  const submitText =
    labels?.submitButtonLabel ?? labels?.submitCta ?? defaults.submitButtonLabel;
  return {
    cancelButtonLabel: cancelText,
    submitButtonLabel: submitText,
    closeButtonLabel: labels?.closeButtonLabel ?? defaults.closeButtonLabel,
    cancelCta: cancelText,
    submitCta: submitText,
    unsavedAlertTitle: labels?.unsavedAlertTitle ?? defaults.unsavedAlertTitle,
    unsavedAlertMessage:
      labels?.unsavedAlertMessage ?? defaults.unsavedAlertMessage,
    unsavedStayCta: labels?.unsavedStayCta ?? defaults.unsavedStayCta,
    unsavedDiscardCta: labels?.unsavedDiscardCta ?? defaults.unsavedDiscardCta,
  };
}
