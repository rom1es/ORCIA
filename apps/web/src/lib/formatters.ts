export type SupportedUiLocale = "fr" | "en";

const INTL_LOCALE_BY_UI_LOCALE: Readonly<Record<SupportedUiLocale, string>> = {
  fr: "fr-FR",
  en: "en-US",
};

/**
 * Format a monetary amount in EUR according to the active locale (`fr` -> `12,34 €`, `en` -> `€12.34`).
 */
export function formatCurrency(
  amount: number,
  locale: SupportedUiLocale = "fr",
  options: {
    readonly currency?: "EUR";
    readonly minimumFractionDigits?: number;
    readonly maximumFractionDigits?: number;
  } = {},
): string {
  const safeAmount = Number.isFinite(amount) ? amount : 0;
  const currency = options.currency ?? "EUR";
  const intlLocale = INTL_LOCALE_BY_UI_LOCALE[locale];
  const isMicroAmount = Math.abs(safeAmount) > 0 && Math.abs(safeAmount) < 0.01;
  const minDigits = options.minimumFractionDigits ?? (isMicroAmount ? 3 : 2);
  const maxDigits =
    options.maximumFractionDigits ?? (isMicroAmount ? Math.max(minDigits, 4) : Math.max(minDigits, 2));
  return new Intl.NumberFormat(intlLocale, {
    style: "currency",
    currency,
    minimumFractionDigits: minDigits,
    maximumFractionDigits: maxDigits,
  }).format(safeAmount);
}

/**
 * Format an ISO date or Date instance as a short localized date (`fr` -> `dd/mm/yyyy`, `en` -> `mm/dd/yyyy`).
 */
export function formatShortDate(
  isoOrDate: string | Date,
  locale: SupportedUiLocale = "fr",
): string {
  const parsed = isoOrDate instanceof Date ? isoOrDate : new Date(isoOrDate);
  if (Number.isNaN(parsed.getTime())) {
    return typeof isoOrDate === "string" ? isoOrDate : "";
  }
  const intlLocale = INTL_LOCALE_BY_UI_LOCALE[locale];
  return new Intl.DateTimeFormat(intlLocale, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(parsed);
}

/**
 * Format an ISO timestamp or Date instance with localized UTC date and time (`HH:mm:ss`).
 */
export function formatShortDateTime(
  isoOrDate: string | Date,
  locale: SupportedUiLocale = "fr",
): string {
  const parsed = isoOrDate instanceof Date ? isoOrDate : new Date(isoOrDate);
  if (Number.isNaN(parsed.getTime())) {
    return typeof isoOrDate === "string" ? isoOrDate : "";
  }
  const datePart = formatShortDate(parsed, locale);
  const pad = (n: number) => String(n).padStart(2, "0");
  const timePart = `${pad(parsed.getUTCHours())}:${pad(parsed.getUTCMinutes())}:${pad(parsed.getUTCSeconds())}`;
  return `${datePart} ${timePart}`;
}
