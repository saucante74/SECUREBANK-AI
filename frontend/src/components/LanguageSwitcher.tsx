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
      className="flex h-7 items-center rounded-full border border-border bg-white p-0.5 shadow-sm"
      role="group"
      aria-label={t("app.languageLabel")}
    >
      {supportedLanguages.map((language) => (
        <button
          key={language}
          type="button"
          className={`h-5 min-w-6 rounded-full px-1 font-medium uppercase leading-none tracking-normal transition-colors sm:min-w-7 sm:px-1.5 ${
            language === activeLanguage
              ? "bg-brand-navy text-white shadow-sm"
              : "text-muted hover:bg-surface hover:text-brand-navy"
          }`}
          style={{ fontSize: "12px" }}
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
