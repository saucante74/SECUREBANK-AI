import { useState, type SyntheticEvent } from "react";
import { useTranslation } from "react-i18next";

interface DevelopmentTokenPanelProps {
  hasToken: boolean;
  onClearToken: () => void;
  onUseToken: (token: string) => void;
}

export function DevelopmentTokenPanel({
  hasToken,
  onClearToken,
  onUseToken,
}: DevelopmentTokenPanelProps) {
  const { t } = useTranslation();
  const [tokenDraft, setTokenDraft] = useState("");

  const useToken = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    const token = tokenDraft.trim();
    if (!token) {
      return;
    }
    onUseToken(token);
    setTokenDraft("");
  };

  const clearToken = () => {
    setTokenDraft("");
    onClearToken();
  };

  return (
    <section
      className="rounded-2xl border border-amber-300 bg-amber-50 p-6 text-amber-950 shadow-soft sm:p-8"
      aria-labelledby="development-token-title"
    >
      <h2 id="development-token-title" className="text-xl font-semibold">
        {t("assistant.developmentToken.title")}
      </h2>
      <p className="mt-3 max-w-3xl text-sm leading-6">
        {t("assistant.developmentToken.warning")}
      </p>
      <form className="mt-5" onSubmit={useToken}>
        <label className="block text-sm font-semibold" htmlFor="development-token">
          {t("assistant.developmentToken.label")}
        </label>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-end">
          <input
            id="development-token"
            className="min-h-11 min-w-0 flex-1 rounded-xl border border-amber-300 bg-white px-4 py-3 text-ink shadow-inner"
            type="password"
            autoComplete="off"
            value={tokenDraft}
            placeholder={t("assistant.developmentToken.placeholder")}
            onChange={(event) => {
              setTokenDraft(event.target.value);
            }}
          />
          <div className="flex gap-3">
            <button
              type="submit"
              className="min-h-11 rounded-xl bg-brand-navy px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!tokenDraft.trim()}
            >
              {t("assistant.developmentToken.use")}
            </button>
            <button
              type="button"
              className="min-h-11 rounded-xl border border-amber-400 bg-white px-5 py-3 text-sm font-semibold text-amber-950 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={!hasToken && !tokenDraft}
              onClick={clearToken}
            >
              {t("assistant.developmentToken.clear")}
            </button>
          </div>
        </div>
      </form>
      <p className="mt-4 text-sm font-semibold" aria-live="polite">
        {hasToken
          ? t("assistant.developmentToken.active")
          : t("assistant.developmentToken.missing")}
      </p>
    </section>
  );
}
