import { useTranslation } from "react-i18next";

interface SuggestedQuestionsProps {
  disabled: boolean;
  onSelect: (question: string) => void;
}

export function SuggestedQuestions({
  disabled,
  onSelect,
}: SuggestedQuestionsProps) {
  const { t } = useTranslation();
  const questions = [
    t("assistant.suggestions.dailyTransferLimit"),
    t("assistant.suggestions.accountDocuments"),
    t("assistant.suggestions.suspiciousTransaction"),
  ];

  return (
    <section aria-labelledby="suggested-questions-title">
      <div className="flex items-center gap-2 text-muted">
        <svg
          aria-hidden="true"
          className="size-4 text-accent-strong"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M9 18h6M10 22h4" />
          <path d="M8.5 14.5a7 7 0 1 1 7 0c-.9.7-1.5 1.6-1.5 2.5h-4c0-.9-.6-1.8-1.5-2.5Z" />
        </svg>
        <h2
          id="suggested-questions-title"
          className="font-sans text-xs font-semibold uppercase tracking-[0.14em]"
        >
          {t("assistant.suggestions.title")}
        </h2>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        {questions.map((question) => (
          <button
            key={question}
            type="button"
            className="group flex min-h-16 items-center gap-3 rounded-xl border border-border bg-white px-4 py-3 text-left text-sm leading-5 text-ink shadow-soft transition-colors hover:border-accent/60 hover:bg-accent-soft disabled:cursor-not-allowed disabled:bg-surface disabled:text-muted disabled:opacity-65"
            disabled={disabled}
            onClick={() => {
              onSelect(question);
            }}
          >
            <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-surface text-muted transition-colors group-hover:bg-white group-hover:text-accent-strong" aria-hidden="true">
              <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 5h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H9l-5 4V7a2 2 0 0 1 2-2Z" />
              </svg>
            </span>
            <span>{question}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
