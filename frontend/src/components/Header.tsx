import { useCallback, useRef, useState, type RefObject } from "react";
import { useTranslation } from "react-i18next";

import { LanguageSwitcher } from "./LanguageSwitcher";
import { LoginDialog } from "./LoginDialog";
import { LogoutConfirmationDialog } from "./LogoutConfirmationDialog";
import type { AuthMeResponse, LoginRequest } from "../api/types";
import type { ApiErrorTranslationKey } from "../i18n/apiErrorKeys";
import type { AuthStatus } from "../hooks/useAuthSession";

interface HeaderProps {
  authStatus: AuthStatus;
  isMenuOpen: boolean;
  logoutErrorKey?: ApiErrorTranslationKey;
  menuButtonRef: RefObject<HTMLButtonElement | null>;
  onLogin: (credentials: LoginRequest) => Promise<void>;
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
  onLogin,
  onLogout,
  onMenuOpen,
  pageTitle,
  user,
}: HeaderProps) {
  const { t } = useTranslation();
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isLogoutOpen, setIsLogoutOpen] = useState(false);
  const loginButtonRef = useRef<HTMLButtonElement>(null);
  const logoutButtonRef = useRef<HTMLButtonElement>(null);
  const closeLogin = useCallback(() => {
    setIsLoginOpen(false);
  }, []);
  const closeLogout = useCallback(() => {
    setIsLogoutOpen(false);
  }, []);

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-white px-4 py-3 sm:px-6 lg:px-8 xl:px-10">
      <div className="mx-auto flex min-h-12 w-full max-w-5xl items-center justify-between gap-4">
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
            <p className="text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-muted sm:text-xs">
              {t("app.dashboard")}
            </p>
            <p className="mt-0.5 truncate font-display text-lg font-bold text-ink sm:text-xl">
              {pageTitle}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {authStatus === "authenticated" && user && (
            <span className="hidden rounded-full border border-accent/25 bg-accent-soft px-3 py-1.5 text-xs font-semibold text-accent-strong md:inline-flex">
              {t("auth.connected", { role: user.role })}
            </span>
          )}
          <LanguageSwitcher />
          {authStatus === "anonymous" && (
            <button
              ref={loginButtonRef}
              type="button"
              className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-border bg-white px-3 text-sm font-semibold text-brand-navy transition-colors hover:border-accent/50 hover:bg-accent-soft hover:text-accent-strong"
              aria-label={t("auth.login.submit")}
              onClick={() => {
                setIsLoginOpen(true);
              }}
            >
              <svg
                aria-hidden="true"
                className="size-[1.125rem]"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M14 7l5 5-5 5M19 12H8" />
                <path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4" />
              </svg>
              <span>{t("auth.login.submit")}</span>
            </button>
          )}
          {authStatus === "authenticated" && user && (
            <button
                ref={logoutButtonRef}
                type="button"
                className="inline-flex size-8 items-center justify-center rounded-lg border border-border bg-white text-brand-navy transition-colors hover:border-accent/50 hover:bg-accent-soft hover:text-accent-strong"
                aria-label={t("auth.logout")}
                onClick={() => {
                  setIsLogoutOpen(true);
                }}
              >
                <svg
                  aria-hidden="true"
                  className="size-[1.125rem]"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M10 17l5-5-5-5M15 12H3" />
                  <path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4" />
                </svg>
            </button>
          )}
        </div>
      </div>
      {logoutErrorKey && (
        <p className="mx-auto mt-3 w-full max-w-5xl rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
          {t(logoutErrorKey)}
        </p>
      )}
      <LoginDialog
        isOpen={isLoginOpen}
        onCancel={closeLogin}
        onLogin={onLogin}
        onSuccess={closeLogin}
        returnFocusRef={loginButtonRef}
      />
      <LogoutConfirmationDialog
        isOpen={isLogoutOpen}
        onCancel={closeLogout}
        onConfirm={onLogout}
        returnFocusRef={logoutButtonRef}
      />
    </header>
  );
}
