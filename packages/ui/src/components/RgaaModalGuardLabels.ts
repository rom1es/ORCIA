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
