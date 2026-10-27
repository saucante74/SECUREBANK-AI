import type { MouseEvent, RefObject } from "react";

import { pathForPage, type PageId } from "../app/navigation";

interface SidebarProps {
  closeButtonRef: RefObject<HTMLButtonElement | null>;
  currentPage: PageId;
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (page: PageId) => void;
}

const navigationItems: { label: string; page: PageId }[] = [
  { label: "Accueil", page: "home" },
  { label: "Assistant", page: "assistant" },
];

export function Sidebar({
  closeButtonRef,
  currentPage,
  isOpen,
  onClose,
  onNavigate,
}: SidebarProps) {
  const visibilityClass = isOpen ? "translate-x-0" : "-translate-x-full";

  const navigate = (event: MouseEvent<HTMLAnchorElement>, page: PageId) => {
    if (
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) {
      return;
    }
    event.preventDefault();
    onNavigate(page);
  };

  return (
    <aside
      id="app-navigation"
      className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col bg-brand-navy text-white shadow-panel transition-transform duration-200 ease-out lg:translate-x-0 ${visibilityClass}`}
      aria-label="Navigation principale"
    >
      <div className="flex items-center justify-between border-b border-white/10 px-6 py-6">
        <div>
          <p className="text-xl font-semibold tracking-tight">SecureBank-AI</p>
          <p className="mt-1 text-xs font-medium uppercase tracking-[0.18em] text-white/60">
            Interface sécurisée
          </p>
        </div>
        <button
          ref={closeButtonRef}
          type="button"
          className="inline-flex size-10 items-center justify-center rounded-xl border border-white/15 text-white lg:hidden"
          aria-label="Fermer le menu"
          tabIndex={isOpen ? 0 : -1}
          onClick={onClose}
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
            <path d="m6 6 12 12M18 6 6 18" />
          </svg>
        </button>
      </div>

      <nav className="flex-1 px-4 py-6" aria-label="Sections de l’application">
        <p className="px-3 text-xs font-semibold uppercase tracking-[0.16em] text-white/45">
          Navigation
        </p>
        <ul className="mt-3 space-y-2">
          {navigationItems.map(({ label, page }) => {
            const isCurrent = currentPage === page;
            const stateClass = isCurrent
              ? "bg-white/12 font-semibold text-white ring-1 ring-inset ring-white/15"
              : "font-medium text-white/70 hover:bg-white/8 hover:text-white";

            return (
              <li key={page}>
                <a
                  className={`flex items-center justify-between rounded-xl px-4 py-3 text-sm transition-colors ${stateClass}`}
                  href={pathForPage(page)}
                  aria-current={isCurrent ? "page" : undefined}
                  onClick={(event) => {
                    navigate(event, page);
                  }}
                >
                  <span>{label}</span>
                  {isCurrent && (
                    <span
                      className="size-2 rounded-full bg-accent"
                      aria-hidden="true"
                    />
                  )}
                </a>
              </li>
            );
          })}
          <li>
            <div className="flex cursor-not-allowed items-center justify-between rounded-xl px-4 py-3 text-sm font-medium text-white/55">
              <span>À propos</span>
              <span className="rounded-full border border-white/10 px-2 py-0.5 text-[0.625rem] font-semibold uppercase tracking-wider text-white/45">
                À venir
              </span>
            </div>
          </li>
        </ul>
      </nav>

      <div className="border-t border-white/10 p-6">
        <div className="rounded-2xl bg-brand-deep p-4 ring-1 ring-inset ring-white/10">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-accent">
            Démonstration
          </p>
          <p className="mt-2 text-sm leading-6 text-white/65">
            Interface de présentation utilisant exclusivement des données
            synthétiques.
          </p>
        </div>
      </div>
    </aside>
  );
}
