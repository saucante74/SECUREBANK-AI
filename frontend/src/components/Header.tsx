import type { RefObject } from "react";

interface HeaderProps {
  isMenuOpen: boolean;
  menuButtonRef: RefObject<HTMLButtonElement | null>;
  onMenuOpen: () => void;
  pageTitle: string;
}

export function Header({
  isMenuOpen,
  menuButtonRef,
  onMenuOpen,
  pageTitle,
}: HeaderProps) {
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
            aria-label="Ouvrir la navigation"
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
              Tableau de bord
            </p>
            <p className="truncate text-lg font-semibold text-brand-navy">
              {pageTitle}
            </p>
          </div>
        </div>
        <span className="rounded-full border border-accent/25 bg-accent-soft px-3 py-1.5 text-xs font-semibold text-accent-strong sm:text-sm">
          Environnement de démonstration
        </span>
      </div>
    </header>
  );
}
