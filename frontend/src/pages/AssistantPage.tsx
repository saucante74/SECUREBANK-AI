import {
  useCallback,
  useRef,
  useState,
  type SyntheticEvent,
} from "react";
import { useTranslation } from "react-i18next";

import { LoginDialog } from "../components/LoginDialog";
import { RagLoadingPanel } from "../components/RagLoadingPanel";
import { RagResponsePanel } from "../components/RagResponsePanel";
import { SuggestedQuestions } from "../components/SuggestedQuestions";
import type { LoginRequest } from "../api/types";
import type { AuthStatus } from "../hooks/useAuthSession";
import { useRagRequest } from "../hooks/useRagRequest";

const questionLimit = 2_000;

interface AssistantPageProps {
  authStatus?: AuthStatus;
  onLogin?: (credentials: LoginRequest) => Promise<void>;
  onSessionExpired?: () => void;
}

export function AssistantPage({
  authStatus = "anonymous",
  onLogin,
  onSessionExpired,
}: AssistantPageProps) {
  const { t } = useTranslation();
  const [question, setQuestion] = useState("");
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const sendButtonRef = useRef<HTMLButtonElement>(null);
  const requireAuthentication = useCallback(() => {
    onSessionExpired?.();
    setIsLoginOpen(true);
  }, [onSessionExpired]);
  const { errorKey, isLoading, response, submit } = useRagRequest(
    requireAuthentication,
  );
  const isQuestionValid =
    question.length >= 1 &&
    question.length <= questionLimit &&
    Boolean(question.trim());
  const canSubmit = isQuestionValid && !isLoading;

  const submitQuestion = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }
    if (authStatus !== "authenticated") {
      setIsLoginOpen(true);
      return;
    }
    void submit(question);
  };

  const login = async (credentials: LoginRequest) => {
    if (!onLogin) {
      throw new Error("Authentication unavailable");
    }
    await onLogin(credentials);
  };

  const finishLogin = () => {
    setIsLoginOpen(false);
    void submit(question);
  };

  return (
    <div className="space-y-6 sm:space-y-8">
      <section aria-labelledby="assistant-page-title">
        <p className="text-sm font-semibold uppercase tracking-[0.14em] text-accent-strong">
          {t("assistant.eyebrow")}
        </p>
        <h1
          id="assistant-page-title"
          className="mt-3 text-3xl font-extrabold tracking-tight text-ink sm:text-4xl"
        >
          {t("assistant.title")}
        </h1>
        <p className="mt-3 max-w-3xl text-base leading-7 text-muted sm:text-lg">
          {t("assistant.description")}
        </p>
      </section>

      <div aria-busy={isLoading}>
        {isLoading ? (
          <RagLoadingPanel />
        ) : errorKey ? (
          <section
            className="rounded-2xl border border-red-200 bg-white p-5 text-red-950 shadow-soft sm:p-6"
            role="alert"
          >
            <h2 className="text-xl font-semibold">{t("assistant.errorTitle")}</h2>
            <p className="mt-3 leading-7">{t(errorKey)}</p>
          </section>
        ) : (
          <RagResponsePanel response={response} />
        )}
      </div>

      <section
        className="overflow-hidden rounded-2xl border border-border bg-white shadow-soft"
        aria-labelledby="question-form-title"
      >
        <form onSubmit={submitQuestion}>
          <div className="p-5 sm:p-6">
            <h2 id="question-form-title" className="text-xl font-bold text-ink sm:text-2xl">
              {t("assistant.questionSection")}
            </h2>
            <label
              className="mt-4 block text-sm font-semibold text-brand-navy"
              htmlFor="rag-question"
            >
              {t("assistant.questionLabel")}
            </label>
            <textarea
              id="rag-question"
              className="mt-2 min-h-32 w-full resize-y rounded-xl border border-border bg-[#fbfbfc] px-4 py-3 text-base leading-7 text-ink shadow-inner placeholder:text-muted/70 sm:min-h-36"
              value={question}
              maxLength={questionLimit}
              placeholder={t("assistant.placeholder")}
              aria-describedby="question-counter assistant-availability"
              onChange={(event) => {
                setQuestion(event.target.value);
              }}
            />
            <div className="mt-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <p
                id="question-counter"
                className="text-sm text-muted"
                aria-live="polite"
              >
                {t("assistant.characterCount", {
                  current: question.length,
                  maximum: questionLimit,
                })}
              </p>
              <button
                ref={sendButtonRef}
                type="submit"
                className="inline-flex min-h-10 items-center justify-center rounded-lg bg-brand-navy px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-active disabled:cursor-not-allowed disabled:bg-[#d5dae0] disabled:text-[#9ba6b2]"
                disabled={!canSubmit}
              >
                {t("assistant.send")}
              </button>
            </div>
          </div>
          <p
            id="assistant-availability"
            className="flex min-h-16 items-center gap-3 border-t border-accent/15 bg-accent-soft px-5 py-3 text-sm leading-6 text-accent-strong sm:px-6"
          >
            <svg aria-hidden="true" className="size-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="9" />
              <path strokeLinecap="round" d="M12 11v6m0-10h.01" />
            </svg>
            <span>
              {authStatus === "authenticated"
                ? t("assistant.authenticatedReady")
                : t("assistant.loginRequired")}
            </span>
          </p>
        </form>
      </section>
      <SuggestedQuestions
        disabled={isLoading}
        onSelect={(suggestedQuestion) => {
          setQuestion(suggestedQuestion);
        }}
      />
      <LoginDialog
        isOpen={isLoginOpen}
        onCancel={() => {
          setIsLoginOpen(false);
        }}
        onLogin={login}
        onSuccess={finishLogin}
        returnFocusRef={sendButtonRef}
      />
    </div>
  );
}
