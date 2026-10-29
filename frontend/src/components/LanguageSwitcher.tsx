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
      className="flex h-8 items-center rounded-lg border border-border bg-surface p-0.5"
      role="group"
      aria-label={t("app.languageLabel")}
    >
      {supportedLanguages.map((language) => (
        <button
          key={language}
          type="button"
          className={`h-[1.625rem] min-w-7 rounded-md px-1.5 text-[0.625rem] font-semibold uppercase tracking-wide transition-colors sm:min-w-8 ${
            language === activeLanguage
              ? "bg-accent text-brand-navy shadow-sm"
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
