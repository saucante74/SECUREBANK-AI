import { useState, type SyntheticEvent } from "react";
import { useTranslation } from "react-i18next";

import { DevelopmentTokenPanel } from "../components/DevelopmentTokenPanel";
import { RagResponsePanel } from "../components/RagResponsePanel";
import { useRagRequest } from "../hooks/useRagRequest";

const questionLimit = 2_000;

interface AssistantPageProps {
  isDevelopment?: boolean;
}

export function AssistantPage({
  isDevelopment = import.meta.env.DEV,
}: AssistantPageProps) {
  const { t } = useTranslation();
  const developmentMode = import.meta.env.DEV && isDevelopment;
  const [question, setQuestion] = useState("");
  const [token, setToken] = useState("");
  const { errorKey, isLoading, reset, response, submit } = useRagRequest();
  const isQuestionValid =
    question.length >= 1 &&
    question.length <= questionLimit &&
    Boolean(question.trim());
  const canSubmit =
    developmentMode && Boolean(token) && isQuestionValid && !isLoading;

  const submitQuestion = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }
    void submit(question, token);
  };

  const useToken = (nextToken: string) => {
    reset();
    setToken(nextToken);
  };

  const clearToken = () => {
    reset();
    setToken("");
  };

  return (
    <div className="space-y-8 sm:space-y-10">
      <section aria-labelledby="assistant-page-title">
        <p className="text-sm font-semibold text-accent-strong">
          {t("assistant.eyebrow")}
        </p>
        <h1
          id="assistant-page-title"
          className="mt-3 text-3xl font-semibold tracking-tight text-brand-navy sm:text-4xl"
        >
          {t("assistant.title")}
        </h1>
        <p className="mt-4 max-w-3xl text-lg leading-8 text-muted">
          {t("assistant.description")}
        </p>
      </section>

      {developmentMode ? (
        <DevelopmentTokenPanel
          hasToken={Boolean(token)}
          onClearToken={clearToken}
          onUseToken={useToken}
        />
      ) : (
        <section
          className="rounded-2xl border border-amber-300 bg-amber-50 p-6 text-amber-950 shadow-soft sm:p-8"
          aria-labelledby="production-auth-title"
        >
          <h2 id="production-auth-title" className="text-xl font-semibold">
            {t("assistant.productionAuth.title")}
          </h2>
          <p className="mt-3 leading-7">
            {t("assistant.productionAuth.description")}
          </p>
        </section>
      )}

      <div aria-busy={isLoading}>
        {isLoading ? (
          <section
            className="flex min-h-64 items-center justify-center rounded-2xl border border-border bg-white p-8 text-center shadow-soft"
            role="status"
          >
            <div>
              <span
                className="mx-auto block size-3 rounded-full bg-accent"
                aria-hidden="true"
              />
              <p className="mt-4 font-semibold text-brand-navy">
                {t("assistant.loading")}
              </p>
            </div>
          </section>
        ) : errorKey ? (
          <section
            className="rounded-2xl border border-red-300 bg-red-50 p-6 text-red-950 shadow-soft sm:p-8"
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
        className="rounded-2xl border border-border bg-white p-6 shadow-soft sm:p-8"
        aria-labelledby="question-form-title"
      >
        <h2 id="question-form-title" className="text-xl font-semibold text-brand-navy">
          {t("assistant.questionSection")}
        </h2>
        <form className="mt-5" onSubmit={submitQuestion}>
          <label
            className="block text-sm font-semibold text-brand-navy"
            htmlFor="rag-question"
          >
            {t("assistant.questionLabel")}
          </label>
          <textarea
            id="rag-question"
            className="mt-2 min-h-36 w-full resize-y rounded-xl border border-border bg-white px-4 py-3 leading-7 text-ink shadow-inner placeholder:text-muted/75"
            value={question}
            maxLength={questionLimit}
            placeholder={t("assistant.placeholder")}
            aria-describedby="question-counter assistant-availability"
            onChange={(event) => {
              setQuestion(event.target.value);
            }}
          />
          <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
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
              type="submit"
              className="inline-flex min-h-11 items-center justify-center rounded-xl bg-brand-navy px-6 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-55"
              disabled={!canSubmit}
            >
              {t("assistant.send")}
            </button>
          </div>
          <p
            id="assistant-availability"
            className="mt-5 rounded-xl border border-accent/25 bg-accent-soft px-4 py-3 text-sm leading-6 text-accent-strong"
          >
            {developmentMode
              ? token
                ? t("assistant.developmentToken.ready")
                : t("assistant.developmentToken.required")
              : t("assistant.productionAuth.formDisabled")}
          </p>
        </form>
      </section>
    </div>
  );
}
