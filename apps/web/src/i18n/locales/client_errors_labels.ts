import type { ClientErrorLabels } from "../../lib/clientErrorCodes";
import { CLIENT_ERRORS_EN_LABELS } from "./client_errors_labels_en";
import { CLIENT_ERRORS_FR_LABELS } from "./client_errors_labels_fr";

export { CLIENT_ERRORS_EN_LABELS, CLIENT_ERRORS_FR_LABELS };

export const CLIENT_ERRORS_BY_LOCALE: Record<"fr" | "en", ClientErrorLabels> = {
  fr: CLIENT_ERRORS_FR_LABELS,
  en: CLIENT_ERRORS_EN_LABELS,
};
