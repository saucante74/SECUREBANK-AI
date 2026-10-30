import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { PageId } from "../app/navigation";
import type { AuthMeResponse, LoginRequest } from "../api/types";
import type { ApiErrorTranslationKey } from "../i18n/apiErrorKeys";
import type { AuthStatus } from "../hooks/useAuthSession";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

interface AppShellProps {
  authStatus: AuthStatus;
  children: ReactNode;
  currentPage: PageId;
  logoutErrorKey?: ApiErrorTranslationKey;
  onNavigate: (page: PageId) => void;
  onLogin: (credentials: LoginRequest) => Promise<void>;
  onLogout: () => Promise<void>;
  pageTitle: string;
  user?: AuthMeResponse;
}

export function AppShell({
  authStatus,
  children,
  currentPage,
  logoutErrorKey,
  onNavigate,
  onLogin,
  onLogout,
  pageTitle,
  user,
}: AppShellProps) {
  const { t } = useTranslation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const closeMenu = useCallback(() => {
    setIsMenuOpen(false);
    menuButtonRef.current?.focus();
  }, []);

  const openMenu = () => {
    setIsMenuOpen(true);
  };

  const navigate = (page: PageId) => {
    onNavigate(page);
    if (isMenuOpen) {
      closeMenu();
    }
  };

  useEffect(() => {
    if (!isMenuOpen) {
      return undefined;
    }

    closeButtonRef.current?.focus();

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeMenu();
      }
    };

    document.addEventListener("keydown", closeOnEscape);

    return () => {
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [closeMenu, isMenuOpen]);

  return (
    <div className="min-h-screen overflow-x-hidden bg-surface text-ink">
      {isMenuOpen && (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-brand-navy/55 lg:hidden"
          aria-label={t("accessibility.closeNavigation")}
          onClick={closeMenu}
        />
      )}
      <Sidebar
        closeButtonRef={closeButtonRef}
        currentPage={currentPage}
        isOpen={isMenuOpen}
        onClose={closeMenu}
        onNavigate={navigate}
        user={user}
      />
      <div className="flex min-h-screen min-w-0 flex-col lg:pl-[17rem] xl:pl-72">
        <Header
          authStatus={authStatus}
          menuButtonRef={menuButtonRef}
          isMenuOpen={isMenuOpen}
          logoutErrorKey={logoutErrorKey}
          onLogin={onLogin}
          onLogout={onLogout}
          onMenuOpen={openMenu}
          pageTitle={pageTitle}
          user={user}
        />
        <main className="flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-8 xl:px-10">
          <div className="mx-auto w-full max-w-5xl">{children}</div>
        </main>
        <footer className="border-t border-border bg-white px-5 py-5 text-center text-sm text-muted sm:px-8 lg:hidden">
          {t("app.footer")}
        </footer>
      </div>
    </div>
  );
}
