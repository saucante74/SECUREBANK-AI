import { useEffect, useRef, useState, type RefObject } from "react";
import { useTranslation } from "react-i18next";

interface LogoutConfirmationDialogProps {
  isOpen: boolean;
  onCancel: () => void;
  onConfirm: () => Promise<void>;
  returnFocusRef: RefObject<HTMLButtonElement | null>;
}

export function LogoutConfirmationDialog({
  isOpen,
  onCancel,
  onConfirm,
  returnFocusRef,
}: LogoutConfirmationDialogProps) {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const cancelButtonRef = useRef<HTMLButtonElement>(null);
  const confirmButtonRef = useRef<HTMLButtonElement>(null);
  const loadingRef = useRef(false);

  useEffect(() => {
    if (!isOpen) return undefined;
    const previousOverflow = document.body.style.overflow;
    const returnFocusElement = returnFocusRef.current;
    document.body.style.overflow = "hidden";
    cancelButtonRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !loadingRef.current) {
        onCancel();
        return;
      }
      if (event.key !== "Tab") return;
      if (event.shiftKey && document.activeElement === cancelButtonRef.current) {
        event.preventDefault();
        confirmButtonRef.current?.focus();
      } else if (
        !event.shiftKey &&
        document.activeElement === confirmButtonRef.current
      ) {
        event.preventDefault();
        cancelButtonRef.current?.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
      returnFocusElement?.focus();
    };
  }, [isOpen, onCancel, returnFocusRef]);

  if (!isOpen) return null;

  const confirm = async () => {
    setIsLoading(true);
    loadingRef.current = true;
    try {
      await onConfirm();
      onCancel();
    } finally {
      loadingRef.current = false;
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-brand-navy/70 p-5 backdrop-blur-sm">
      <section
        className="w-full max-w-md rounded-2xl border border-white/60 bg-white p-5 shadow-panel sm:p-6"
        role="dialog"
        aria-modal="true"
        aria-labelledby="logout-dialog-title"
        aria-describedby="logout-dialog-description"
      >
        <span
          className="flex size-11 items-center justify-center rounded-xl bg-accent-soft text-accent-strong"
          aria-hidden="true"
        >
          <svg
            className="size-5"
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
        </span>
        <h2
          id="logout-dialog-title"
          className="mt-5 font-display text-xl font-extrabold text-ink"
        >
          {t("auth.logoutConfirmation.title")}
        </h2>
        <p id="logout-dialog-description" className="mt-3 leading-7 text-muted">
          {t("auth.logoutConfirmation.description")}
        </p>
        <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button
            ref={cancelButtonRef}
            type="button"
            className="min-h-10 rounded-lg border border-border bg-white px-5 py-2.5 text-sm font-semibold text-brand-navy transition-colors hover:bg-surface"
            disabled={isLoading}
            onClick={onCancel}
          >
            {t("auth.logoutConfirmation.cancel")}
          </button>
          <button
            ref={confirmButtonRef}
            type="button"
            className="min-h-10 rounded-lg bg-brand-navy px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-active disabled:cursor-not-allowed disabled:bg-[#d5dae0] disabled:text-[#9ba6b2]"
            disabled={isLoading}
            onClick={() => void confirm()}
          >
            {isLoading
              ? t("auth.logoutConfirmation.loading")
              : t("auth.logoutConfirmation.confirm")}
          </button>
        </div>
      </section>
    </div>
  );
}
