import { useTranslation } from "react-i18next";

import {
  changeLanguage,
  isSupportedLanguage,
  supportedLanguages,
} from "../i18n";

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const activeLanguage = isSupportedLanguage(i18n.resolvedLanguage)
    ? i18n.resolvedLanguage
    : "fr";

  return (
    <div
      className="flex rounded-full border border-border bg-surface p-1 shadow-inner"
      role="group"
      aria-label={t("app.languageLabel")}
    >
        {supportedLanguages.map((language) => (
        <button
          key={language}
          type="button"
          className={`min-h-10 min-w-11 rounded-full px-3 text-sm font-semibold uppercase transition-colors sm:min-w-14 ${
            language === activeLanguage
              ? "bg-ink text-white shadow-soft"
              : "text-muted hover:bg-white hover:text-ink"
          }`}
          aria-pressed={language === activeLanguage}
          aria-label={t(`app.languages.${language}`)}
          onClick={() => {
            void changeLanguage(language);
          }}
        >
          {language}
        </button>
      ))}
    </div>
  );
}
