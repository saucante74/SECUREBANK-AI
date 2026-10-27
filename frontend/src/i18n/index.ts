import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";
import fr from "./locales/fr.json";
import it from "./locales/it.json";

export const supportedLanguages = ["fr", "en", "it"] as const;
export type SupportedLanguage = (typeof supportedLanguages)[number];

export const languageStorageKey = "securebank.language";

interface LanguageStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export function isSupportedLanguage(value: unknown): value is SupportedLanguage {
  return supportedLanguages.some((language) => language === value);
}

export function readLanguagePreference(
  storage?: LanguageStorage,
): SupportedLanguage {
  try {
    const value = (storage ?? window.localStorage).getItem(languageStorageKey);
    return isSupportedLanguage(value) ? value : "fr";
  } catch {
    return "fr";
  }
}

function storeLanguagePreference(
  language: SupportedLanguage,
  storage?: LanguageStorage,
): void {
  try {
    (storage ?? window.localStorage).setItem(languageStorageKey, language);
  } catch {
    return;
  }
}

const initialLanguage = readLanguagePreference();

void i18n.use(initReactI18next).init({
  resources: {
    fr: { translation: fr },
    en: { translation: en },
    it: { translation: it },
  },
  lng: initialLanguage,
  fallbackLng: "fr",
  supportedLngs: supportedLanguages,
  interpolation: { escapeValue: false },
  initAsync: false,
});

document.documentElement.lang = initialLanguage;

i18n.on("languageChanged", (language) => {
  document.documentElement.lang = isSupportedLanguage(language) ? language : "fr";
});

export async function changeLanguage(language: SupportedLanguage): Promise<void> {
  storeLanguagePreference(language);
  await i18n.changeLanguage(language);
}

export default i18n;
