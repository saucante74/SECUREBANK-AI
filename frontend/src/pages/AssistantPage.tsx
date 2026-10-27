import { useState, type SyntheticEvent } from "react";
import { useTranslation } from "react-i18next";

import { RagResponsePanel } from "../components/RagResponsePanel";

const questionLimit = 2_000;

export function AssistantPage() {
  const { t } = useTranslation();
  const [question, setQuestion] = useState("");

  const preventSubmission = (event: SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
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

      <RagResponsePanel />

      <section
        className="rounded-2xl border border-border bg-white p-6 shadow-soft sm:p-8"
        aria-labelledby="question-form-title"
      >
        <h2 id="question-form-title" className="text-xl font-semibold text-brand-navy">
          {t("assistant.questionSection")}
        </h2>
        <form className="mt-5" onSubmit={preventSubmission}>
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
              className="inline-flex min-h-11 items-center justify-center rounded-xl bg-brand-navy px-6 py-3 text-sm font-semibold text-white opacity-55"
              disabled
            >
              {t("assistant.send")}
            </button>
          </div>
          <p
            id="assistant-availability"
            className="mt-5 rounded-xl border border-accent/25 bg-accent-soft px-4 py-3 text-sm leading-6 text-accent-strong"
          >
            {t("assistant.availability")}
          </p>
        </form>
      </section>
    </div>
  );
}
