import {
  useEffect,
  useRef,
  useState,
  type RefObject,
  type SyntheticEvent,
} from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../api/client";
import type { LoginRequest } from "../api/types";

interface LoginDialogProps {
  isOpen: boolean;
  onCancel: () => void;
  onLogin: (credentials: LoginRequest) => Promise<void>;
  onSuccess: () => void;
  returnFocusRef: RefObject<HTMLButtonElement | null>;
}

export function LoginDialog({
  isOpen,
  onCancel,
  onLogin,
  onSuccess,
  returnFocusRef,
}: LoginDialogProps) {
  const { t } = useTranslation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorKey, setErrorKey] = useState<string>();
  const usernameRef = useRef<HTMLInputElement>(null);
  const cancelButtonRef = useRef<HTMLButtonElement>(null);
  const submitButtonRef = useRef<HTMLButtonElement>(null);
  const loadingRef = useRef(false);

  useEffect(() => {
    if (!isOpen) return undefined;
    const previousOverflow = document.body.style.overflow;
    const returnFocusElement = returnFocusRef.current;
    document.body.style.overflow = "hidden";
    usernameRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !loadingRef.current) {
        onCancel();
        return;
      }
      if (event.key !== "Tab") return;
      if (event.shiftKey && document.activeElement === usernameRef.current) {
        event.preventDefault();
        const lastFocusableElement = submitButtonRef.current?.disabled
          ? cancelButtonRef.current
          : submitButtonRef.current;
        lastFocusableElement?.focus();
      } else if (
        !event.shiftKey &&
        (document.activeElement === submitButtonRef.current ||
          (submitButtonRef.current?.disabled &&
            document.activeElement === cancelButtonRef.current))
      ) {
        event.preventDefault();
        usernameRef.current?.focus();
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

  const submit = async (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorKey(undefined);
    setIsLoading(true);
    loadingRef.current = true;
    try {
      await onLogin({ username, password });
      setPassword("");
      onSuccess();
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 429) {
        setErrorKey("auth.login.rateLimited");
      } else if (error instanceof ApiError && error.status === 401) {
        setErrorKey("auth.login.invalidCredentials");
      } else {
        setErrorKey("auth.login.unavailable");
      }
    } finally {
      loadingRef.current = false;
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-brand-navy/70 p-5 backdrop-blur-sm">
      <section
        className="w-full max-w-md rounded-3xl border border-white/60 bg-white p-6 shadow-panel sm:p-8"
        role="dialog"
        aria-modal="true"
        aria-labelledby="login-dialog-title"
        aria-describedby="login-dialog-description"
      >
        <span className="flex size-12 items-center justify-center rounded-2xl bg-accent-soft text-accent-strong" aria-hidden="true">
          <svg className="size-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <rect x="5" y="10" width="14" height="10" rx="2" />
            <path d="M8 10V7a4 4 0 0 1 8 0v3" />
          </svg>
        </span>
        <p className="mt-5 text-sm font-semibold uppercase tracking-[0.12em] text-accent-strong">
          {t("auth.login.eyebrow")}
        </p>
        <h2
          id="login-dialog-title"
          className="mt-2 text-2xl font-extrabold text-ink sm:text-3xl"
        >
          {t("auth.login.title")}
        </h2>
        <p id="login-dialog-description" className="mt-3 leading-7 text-muted">
          {t("auth.login.description")}
        </p>
        <form
          className="mt-6 space-y-5"
          onSubmit={(event) => {
            void submit(event);
          }}
        >
          <div>
            <label
              className="block text-sm font-semibold text-brand-navy"
              htmlFor="login-username"
            >
              {t("auth.login.username")}
            </label>
            <input
              ref={usernameRef}
              id="login-username"
              className="mt-2 min-h-12 w-full rounded-xl border border-border bg-[#fbfbfc] px-4 py-3 text-ink shadow-inner"
              autoComplete="username"
              disabled={isLoading}
              required
              value={username}
              onChange={(event) => {
                setUsername(event.target.value);
              }}
            />
          </div>
          <div>
            <label
              className="block text-sm font-semibold text-brand-navy"
              htmlFor="login-password"
            >
              {t("auth.login.password")}
            </label>
            <input
              id="login-password"
              className="mt-2 min-h-12 w-full rounded-xl border border-border bg-[#fbfbfc] px-4 py-3 text-ink shadow-inner"
              type="password"
              autoComplete="current-password"
              disabled={isLoading}
              required
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
              }}
            />
          </div>
          {errorKey && (
            <p
              className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-950"
              role="alert"
            >
              {t(errorKey)}
            </p>
          )}
          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <button
              ref={cancelButtonRef}
              type="button"
              className="min-h-12 rounded-xl border border-border bg-white px-5 py-3 text-sm font-semibold text-brand-navy transition-colors hover:bg-surface"
              disabled={isLoading}
              onClick={onCancel}
            >
              {t("auth.login.cancel")}
            </button>
            <button
              ref={submitButtonRef}
              type="submit"
              className="min-h-12 rounded-xl bg-brand-navy px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-brand-active disabled:cursor-not-allowed disabled:bg-[#d5dae0] disabled:text-[#9ba6b2]"
              disabled={isLoading || !username.trim() || !password}
            >
              {isLoading ? t("auth.login.loading") : t("auth.login.submit")}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
