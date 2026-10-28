import type { RefObject } from "react";
import { useTranslation } from "react-i18next";

import { LanguageSwitcher } from "./LanguageSwitcher";
import type { AuthMeResponse } from "../api/types";
import type { ApiErrorTranslationKey } from "../i18n/apiErrorKeys";
import type { AuthStatus } from "../hooks/useAuthSession";

interface HeaderProps {
  authStatus: AuthStatus;
  isMenuOpen: boolean;
  logoutErrorKey?: ApiErrorTranslationKey;
  menuButtonRef: RefObject<HTMLButtonElement | null>;
  onLogout: () => Promise<void>;
  onMenuOpen: () => void;
  pageTitle: string;
  user?: AuthMeResponse;
}

export function Header({
  authStatus,
  isMenuOpen,
  logoutErrorKey,
  menuButtonRef,
  onLogout,
  onMenuOpen,
  pageTitle,
  user,
}: HeaderProps) {
  const { t } = useTranslation();

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-white/95 px-5 py-4 backdrop-blur sm:px-8 lg:px-12">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <button
            ref={menuButtonRef}
            type="button"
            className="inline-flex size-11 shrink-0 items-center justify-center rounded-xl border border-border bg-white text-brand-navy shadow-soft lg:hidden"
            aria-controls="app-navigation"
            aria-expanded={isMenuOpen}
            aria-label={t("accessibility.openNavigation")}
            onClick={onMenuOpen}
          >
            <svg
              aria-hidden="true"
              className="size-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <path d="M4 7h16M4 12h16M4 17h16" />
            </svg>
          </button>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
              {t("app.dashboard")}
            </p>
            <p className="truncate text-lg font-semibold text-brand-navy">
              {pageTitle}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          {authStatus === "authenticated" && user && (
            <div className="flex items-center gap-2">
              <span className="hidden rounded-full border border-accent/25 bg-accent-soft px-3 py-1.5 text-xs font-semibold text-accent-strong md:inline-flex">
                {t("auth.connected", { role: user.role })}
              </span>
              <button
                type="button"
                className="min-h-10 rounded-xl border border-border bg-white px-3 py-2 text-xs font-semibold text-brand-navy"
                onClick={() => void onLogout()}
              >
                {t("auth.logout")}
              </button>
            </div>
          )}
          <LanguageSwitcher />
          <span className="hidden rounded-full border border-accent/25 bg-accent-soft px-3 py-1.5 text-xs font-semibold text-accent-strong sm:inline-flex lg:text-sm">
            {t("app.demoEnvironment")}
          </span>
        </div>
      </div>
      {logoutErrorKey && (
        <p className="mx-auto mt-3 w-full max-w-6xl text-sm text-red-800" role="alert">
          {t(logoutErrorKey)}
        </p>
      )}
    </header>
  );
}
