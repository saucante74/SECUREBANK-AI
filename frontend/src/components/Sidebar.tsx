import type { RefObject } from "react";

interface SidebarProps {
  closeButtonRef: RefObject<HTMLButtonElement | null>;
  isOpen: boolean;
  onClose: () => void;
}

const futureNavigationItems = ["Assistant", "À propos"];

export function Sidebar({
  closeButtonRef,
  isOpen,
  onClose,
}: SidebarProps) {
  const visibilityClass = isOpen ? "translate-x-0" : "-translate-x-full";

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
          <li>
            <div
              className="flex items-center justify-between rounded-xl bg-white/12 px-4 py-3 text-sm font-semibold text-white ring-1 ring-inset ring-white/15"
              aria-current="page"
            >
              <span>Accueil</span>
              <span className="size-2 rounded-full bg-accent" aria-hidden="true" />
            </div>
          </li>
          {futureNavigationItems.map((item) => (
            <li key={item}>
              <div className="flex cursor-not-allowed items-center justify-between rounded-xl px-4 py-3 text-sm font-medium text-white/55">
                <span>{item}</span>
                <span className="rounded-full border border-white/10 px-2 py-0.5 text-[0.625rem] font-semibold uppercase tracking-wider text-white/45">
                  À venir
                </span>
              </div>
            </li>
          ))}
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
