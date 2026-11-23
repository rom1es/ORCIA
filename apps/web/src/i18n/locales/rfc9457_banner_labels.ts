import { RFC9457_BANNER_EN_LABELS } from "./rfc9457_banner_labels_en";
import { RFC9457_BANNER_FR_LABELS } from "./rfc9457_banner_labels_fr";

export interface BannerErrorCopy {
  readonly title: string;
  readonly message: string;
  readonly remediation: string;
}

export interface Rfc9457BannerDictionary {
  readonly catalog: Record<string, BannerErrorCopy>;
  readonly statusFallbacks: {
    readonly 401: BannerErrorCopy;
    readonly 403: BannerErrorCopy;
    readonly 404: BannerErrorCopy;
    readonly 409: BannerErrorCopy;
    readonly 422: BannerErrorCopy;
    readonly 503: BannerErrorCopy;
    readonly default: BannerErrorCopy;
  };
  readonly quotedTargetPattern: string;
  readonly prepositionTargetPattern: string;
  readonly fallbackOperationTarget: string;
  readonly resourceSuffixPattern: string;
  readonly sanitizeReplacements: {
    readonly readOnlyObserver: string;
    readonly humanAuthoredRequired: string;
    readonly autonomousContract: string;
    readonly highCritical: string;
  };
}

export { RFC9457_BANNER_EN_LABELS, RFC9457_BANNER_FR_LABELS };

export const RFC9457_BANNER_BY_LOCALE: Record<"fr" | "en", Rfc9457BannerDictionary> = {
  fr: RFC9457_BANNER_FR_LABELS,
  en: RFC9457_BANNER_EN_LABELS,
};
