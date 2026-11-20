export type SupportedUiLocale = "fr" | "en";

/**
 * Formate un montant monétaire en Euro (`EUR`) selon la locale (`fr` -> `12,34 €`, `en` -> `€12.34`).
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
  const intlLocale = locale === "en" ? "en-US" : "fr-FR";
  const isMicroAmount = Math.abs(safeAmount) > 0 && Math.abs(safeAmount) < 0.01;
  const minDigits = options.minimumFractionDigits ?? (isMicroAmount ? 3 : 2);
  const maxDigits = options.maximumFractionDigits ?? (isMicroAmount ? Math.max(minDigits, 4) : Math.max(minDigits, 2));
  return new Intl.NumberFormat(intlLocale, {
    style: "currency",
    currency,
    minimumFractionDigits: minDigits,
    maximumFractionDigits: maxDigits,
  }).format(safeAmount);
}

/**
 * Formate une date ISO en format court localisé (`fr` -> `jj/mm/aaaa`, `en` -> `mm/dd/yyyy`).
 */
export function formatShortDate(
  isoOrDate: string | Date,
  locale: SupportedUiLocale = "fr",
): string {
  const parsed = isoOrDate instanceof Date ? isoOrDate : new Date(isoOrDate);
  if (Number.isNaN(parsed.getTime())) {
    return typeof isoOrDate === "string" ? isoOrDate : "";
  }
  const intlLocale = locale === "en" ? "en-US" : "fr-FR";
  return new Intl.DateTimeFormat(intlLocale, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(parsed);
}

/**
 * Formate un horodatage ISO complet avec date localisée (`jj/mm/aaaa HH:mm:ss` en français).
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
