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
    <div className="flex items-center gap-2">
      <label className="sr-only" htmlFor="interface-language">
        {t("app.languageLabel")}
      </label>
      <select
        id="interface-language"
        className="min-h-10 rounded-lg border border-border bg-white px-3 py-2 text-sm font-semibold text-brand-navy shadow-soft"
        value={activeLanguage}
        onChange={(event) => {
          const language = event.target.value;
          if (isSupportedLanguage(language)) {
            void changeLanguage(language);
          }
        }}
      >
        {supportedLanguages.map((language) => (
          <option key={language} value={language}>
            {t(`app.languages.${language}`)}
          </option>
        ))}
      </select>
    </div>
  );
}
