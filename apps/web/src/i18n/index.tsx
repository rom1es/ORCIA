"use client";

import React, { createContext, useContext, useMemo, useState } from "react";
import { enDictionary } from "./locales/en";
import { frDictionary } from "./locales/fr";
import type { SupportedWebLocale, TranslationDictionary } from "./types";

export const DICTIONARIES: Record<SupportedWebLocale, TranslationDictionary> = {
  fr: frDictionary,
  en: enDictionary,
};

export interface I18nContextValue {
  locale: SupportedWebLocale;
  dictionary: TranslationDictionary;
  setLocale: (nextLocale: SupportedWebLocale) => void;
  toggleLocale: () => void;
}

const I18nContext = createContext<I18nContextValue>({
  locale: "fr",
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

export function useI18n(): I18nContextValue {
  return useContext(I18nContext);
}
