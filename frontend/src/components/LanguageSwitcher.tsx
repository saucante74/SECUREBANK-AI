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
      className="flex rounded-full border border-border bg-surface p-0.5 shadow-inner"
      role="group"
      aria-label={t("app.languageLabel")}
    >
      {supportedLanguages.map((language) => (
        <button
          key={language}
          type="button"
          className={`min-h-8 min-w-9 rounded-full px-2 text-[0.6875rem] font-semibold uppercase transition-colors sm:min-w-10 ${
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
