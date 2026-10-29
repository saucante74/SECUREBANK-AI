import type { RagAskResponse } from "../api/types";
import { useTranslation } from "react-i18next";
import { RagSources } from "./RagSources";

interface RagResponsePanelProps {
  response?: RagAskResponse;
}

export function RagResponsePanel({ response }: RagResponsePanelProps) {
  const { t } = useTranslation();

  if (response === undefined) {
    return (
      <section
        className="flex min-h-80 items-center justify-center rounded-3xl border border-border bg-white p-8 text-center shadow-soft sm:min-h-96"
        aria-labelledby="empty-conversation-title"
      >
        <div className="max-w-md">
          <span className="mx-auto flex size-16 items-center justify-center rounded-2xl bg-surface text-muted" aria-hidden="true">
            <svg className="size-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 5h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H9l-5 4V7a2 2 0 0 1 2-2Z" />
            </svg>
          </span>
          <h2
            id="empty-conversation-title"
            className="mt-7 text-xl font-bold text-ink sm:text-2xl"
          >
            {t("rag.emptyTitle")}
          </h2>
          <p className="mt-3 leading-7 text-muted">
            {t("rag.emptyDescription")}
          </p>
        </div>
      </section>
    );
  }

  return (
    <article className="space-y-7 rounded-3xl border border-border bg-white p-6 shadow-soft sm:p-8">
      <div
        className={
          response.abstained
            ? "rounded-2xl border border-amber-300 bg-amber-50 p-5 text-amber-950"
            : "rounded-2xl border border-accent/25 bg-accent-soft p-5 text-brand-navy"
        }
        role="status"
      >
        <p className="text-sm font-semibold">
          {response.abstained ? t("rag.abstainedStatus") : t("rag.normalStatus")}
        </p>
        {response.abstained && (
          <p className="mt-1 text-sm leading-6">
            {t("rag.abstainedDescription")}
          </p>
        )}
      </div>

      <section aria-labelledby="answer-title">
        <h2 id="answer-title" className="text-xl font-semibold text-brand-navy">
          {t("rag.answerTitle")}
        </h2>
        <p className="mt-4 whitespace-pre-wrap leading-7 text-ink">
          {response.answer}
        </p>
      </section>

      <RagSources citations={response.citations} sources={response.sources} />
    </article>
  );
}
