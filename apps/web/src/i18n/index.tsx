"use client";

import React, { createContext, useContext, useMemo, useState } from "react";
import { enDictionary } from "./locales/en";
import { frDictionary } from "./locales/fr";
import type { SupportedWebLocale, TranslationDictionary } from "./types";

export type { SupportedWebLocale, TranslationDictionary };

export const DICTIONARIES: Record<SupportedWebLocale, TranslationDictionary> = {
  fr: frDictionary,
  en: enDictionary,
};

const IS_FR_BY_LOCALE: Record<SupportedWebLocale, boolean> = {
  fr: true,
  en: false,
};

export interface I18nContextValue {
  locale: SupportedWebLocale;
  isFr: boolean;
  dictionary: TranslationDictionary;
  setLocale: (nextLocale: SupportedWebLocale) => void;
  toggleLocale: () => void;
}

const I18nContext = createContext<I18nContextValue>({
  locale: "fr",
  isFr: true,
  dictionary: frDictionary,
  setLocale: () => undefined,
  toggleLocale: () => undefined,
});

const I18nMountedContext = createContext<boolean>(false);

export interface I18nProviderProps {
  initialLocale?: SupportedWebLocale;
  children: React.ReactNode;
}

export function I18nProvider({ initialLocale = "fr", children }: I18nProviderProps) {
  const hasParentProvider = useContext(I18nMountedContext);
  const [locale, setLocale] = useState<SupportedWebLocale>(initialLocale);

  const value = useMemo<I18nContextValue>(
    () => ({
      locale,
      isFr: IS_FR_BY_LOCALE[locale],
      dictionary: DICTIONARIES[locale],
      setLocale,
      toggleLocale: () => setLocale((prev) => (prev === "fr" ? "en" : "fr")),
    }),
    [locale],
  );

  if (hasParentProvider) {
    return <>{children}</>;
  }

  return (
    <I18nMountedContext.Provider value={true}>
      <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
    </I18nMountedContext.Provider>
  );
}

const FLAG_TO_LOCALE = new Map<boolean, SupportedWebLocale>([
  [true, "fr"],
  [false, "en"],
]);

export function resolveLocaleForFlag(
  isFr?: boolean,
  locale?: SupportedWebLocale,
): SupportedWebLocale {
  if (locale) return locale;
  return FLAG_TO_LOCALE.get(isFr !== false) ?? "fr";
}

export function resolveDictionaryForFlag(
  isFr?: boolean,
  locale?: SupportedWebLocale,
): TranslationDictionary {
  return DICTIONARIES[resolveLocaleForFlag(isFr, locale)];
}

export function formatI18nTemplate(
  template: string,
  params: Readonly<Record<string, string | number>>,
): string {
  return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (_match, key: string) =>
    key in params ? String(params[key]) : `{${key}}`,
  );
}

export function useI18n(): I18nContextValue {
  return useContext(I18nContext);
}
