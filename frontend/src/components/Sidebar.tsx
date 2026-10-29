import type { MouseEvent, RefObject } from "react";
import { useTranslation } from "react-i18next";

import { pathForPage, type PageId } from "../app/navigation";

interface SidebarProps {
  closeButtonRef: RefObject<HTMLButtonElement | null>;
  currentPage: PageId;
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (page: PageId) => void;
}

const navigationItems: { labelKey: string; page: PageId }[] = [
  { labelKey: "navigation.home", page: "home" },
  { labelKey: "navigation.assistant", page: "assistant" },
];

function NavigationIcon({ page }: { page: PageId }) {
  return (
    <svg
      aria-hidden="true"
      className="size-6 shrink-0"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {page === "home" ? (
        <>
          <path d="m3 11 9-8 9 8" />
          <path d="M5 10v10h5v-6h4v6h5V10" />
        </>
      ) : (
        <path d="M5 5h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H9l-5 4V7a2 2 0 0 1 2-2Z" />
      )}
    </svg>
  );
}

export function Sidebar({
  closeButtonRef,
  currentPage,
  isOpen,
  onClose,
  onNavigate,
}: SidebarProps) {
  const { t } = useTranslation();
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
      className={`fixed inset-y-0 left-0 z-40 flex w-80 max-w-[88vw] flex-col bg-brand-navy text-white shadow-panel transition-transform duration-200 ease-out lg:w-80 lg:translate-x-0 xl:w-[22rem] ${visibilityClass}`}
      aria-label={t("accessibility.primaryNavigation")}
    >
      <div className="flex items-center justify-between px-7 py-8 xl:px-8">
        <div className="flex min-w-0 items-center gap-4">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-accent text-brand-navy shadow-soft">
            <svg
              aria-hidden="true"
              className="size-7"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 3 5.5 5.8v5.7c0 4.2 2.7 7.9 6.5 9.5 3.8-1.6 6.5-5.3 6.5-9.5V5.8L12 3Z" />
            </svg>
          </span>
          <div className="min-w-0">
            <p className="truncate font-display text-xl font-extrabold tracking-tight">
              {t("app.name")}
            </p>
            <p className="mt-1 truncate text-xs font-semibold uppercase tracking-[0.18em] text-white/50">
              {t("app.securedInterface")}
            </p>
          </div>
        </div>
        <button
          ref={closeButtonRef}
          type="button"
          className="inline-flex size-10 items-center justify-center rounded-xl border border-white/15 text-white lg:hidden"
          aria-label={t("accessibility.closeMenu")}
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

      <nav
        className="flex-1 px-5 py-8 xl:px-7"
        aria-label={t("accessibility.sectionsNavigation")}
      >
        <p className="px-3 text-sm font-semibold uppercase tracking-[0.18em] text-white/35">
          {t("navigation.title")}
        </p>
        <ul className="mt-5 space-y-2">
          {navigationItems.map(({ labelKey, page }) => {
            const isCurrent = currentPage === page;
            const stateClass = isCurrent
              ? "bg-brand-active font-semibold text-white"
              : "font-medium text-white/60 hover:bg-white/5 hover:text-white";

            return (
              <li key={page}>
                <a
                  className={`flex min-h-14 items-center justify-between rounded-2xl px-4 text-base transition-colors ${stateClass}`}
                  href={pathForPage(page)}
                  aria-current={isCurrent ? "page" : undefined}
                  onClick={(event) => {
                    navigate(event, page);
                  }}
                >
                  <span className="flex items-center gap-4">
                    <NavigationIcon page={page} />
                    <span>{t(labelKey)}</span>
                  </span>
                  {isCurrent && (
                    <span
                      className="size-2.5 rounded-full bg-accent shadow-[0_0_0_5px_rgb(49_217_160_/_0.14)]"
                      aria-hidden="true"
                    />
                  )}
                </a>
              </li>
            );
          })}
          <li>
            <div className="flex min-h-14 cursor-not-allowed items-center justify-between rounded-2xl px-4 text-base font-medium text-white/55">
              <span className="flex items-center gap-4">
                <svg aria-hidden="true" className="size-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <circle cx="12" cy="12" r="9" />
                  <path strokeLinecap="round" d="M12 11v6m0-10h.01" />
                </svg>
                <span>{t("navigation.about")}</span>
              </span>
              <span className="rounded-full bg-white/8 px-3 py-1 text-[0.625rem] font-semibold uppercase tracking-wider text-white/45">
                {t("navigation.comingSoon")}
              </span>
            </div>
          </li>
        </ul>
      </nav>

      <div className="p-6 xl:p-7">
        <div className="rounded-3xl bg-brand-deep p-6 ring-1 ring-inset ring-white/10">
          <p className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.17em] text-accent">
            <span className="size-2 rounded-full bg-accent" aria-hidden="true" />
            <span>{t("app.demo")}</span>
          </p>
          <p className="mt-4 text-sm leading-6 text-white/60">
            {t("app.demoDescription")}
          </p>
        </div>
      </div>
    </aside>
  );
}
