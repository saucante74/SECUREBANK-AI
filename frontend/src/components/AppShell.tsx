import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

interface AppShellProps {
  children: ReactNode;
  pageTitle: string;
}

export function AppShell({ children, pageTitle }: AppShellProps) {
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
          aria-label="Fermer la navigation"
          onClick={closeMenu}
        />
      )}
      <Sidebar
        closeButtonRef={closeButtonRef}
        isOpen={isMenuOpen}
        onClose={closeMenu}
      />
      <div className="flex min-h-screen min-w-0 flex-col lg:pl-72">
        <Header
          menuButtonRef={menuButtonRef}
          isMenuOpen={isMenuOpen}
          onMenuOpen={openMenu}
          pageTitle={pageTitle}
        />
        <main className="flex-1 px-5 py-8 sm:px-8 sm:py-10 lg:px-12 lg:py-12">
          <div className="mx-auto w-full max-w-6xl">{children}</div>
        </main>
        <footer className="border-t border-border bg-white px-5 py-5 text-center text-sm text-muted sm:px-8 lg:text-left">
          SecureBank-AI — Environnement de démonstration
        </footer>
      </div>
    </div>
  );
}
