import { useTranslation } from "react-i18next";

import { InfoCard } from "../components/InfoCard";

const usageSteps = ["question", "login", "answer"] as const;

function UsageStepIcon({ step }: { step: (typeof usageSteps)[number] }) {
  return (
    <svg
      aria-hidden="true"
      className="size-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {step === "question" ? (
        <path d="M5 5h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H9l-5 4V7a2 2 0 0 1 2-2Z" />
      ) : step === "login" ? (
        <>
          <rect x="5" y="10" width="14" height="10" rx="2" />
          <path d="M8 10V7a4 4 0 0 1 8 0v3" />
        </>
      ) : (
        <>
          <path d="M6 3h9l4 4v14H6z" />
          <path d="M15 3v5h5M9 13h6M9 17h6" />
        </>
      )}
    </svg>
  );
}

export function HomePage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6 sm:space-y-8">
      <section aria-labelledby="welcome-title">
        <p className="text-sm font-semibold uppercase tracking-[0.14em] text-accent-strong">
          {t("home.eyebrow")}
        </p>
        <h1
          id="welcome-title"
          className="mt-3 max-w-4xl text-balance text-3xl font-extrabold leading-tight tracking-tight text-ink sm:text-4xl"
        >
          {t("home.title")}
        </h1>
        <p className="mt-3 max-w-3xl text-base leading-7 text-muted sm:text-lg">
          {t("home.description")}
        </p>
      </section>

      <section
        className="relative overflow-hidden rounded-2xl bg-brand-navy px-5 py-6 text-white shadow-panel sm:px-7 sm:py-8"
        aria-labelledby="assistant-title"
      >
        <div className="absolute -right-20 -top-24 size-72 rounded-full bg-accent/15 blur-3xl" />
        <div className="relative max-w-3xl">
          <span className="inline-flex rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-accent">
            {t("home.assistantStatus")}
          </span>
          <h2 id="assistant-title" className="mt-4 text-xl font-bold sm:text-2xl">
            {t("home.assistantTitle")}
          </h2>
          <p className="mt-4 max-w-2xl leading-7 text-white/70">
            {t("home.assistantDescription")}
          </p>
        </div>
      </section>

      <section
        className="grid gap-5 md:grid-cols-2"
        aria-label={t("accessibility.projectPrinciples")}
      >
        <InfoCard
          eyebrow={t("home.privacyEyebrow")}
          title={t("home.privacyTitle")}
          description={t("home.privacyDescription")}
        />
        <InfoCard
          eyebrow={t("home.evidenceEyebrow")}
          title={t("home.evidenceTitle")}
          description={t("home.evidenceDescription")}
        />
      </section>

      <section aria-labelledby="usage-title">
        <h2 id="usage-title" className="text-xl font-bold text-brand-navy">
          {t("home.usage.title")}
        </h2>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {usageSteps.map((step, index) => (
            <article
              key={step}
              className="rounded-xl border border-border bg-white p-4 shadow-soft"
            >
              <div className="flex items-center gap-3">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent-strong">
                  <UsageStepIcon step={step} />
                </span>
                <span className="text-xs font-bold text-accent-strong">
                  {String(index + 1).padStart(2, "0")}
                </span>
              </div>
              <h3 className="mt-3 font-display text-base font-bold text-ink">
                {t(`home.usage.${step}.title`)}
              </h3>
              <p className="mt-2 text-sm leading-6 text-muted">
                {t(`home.usage.${step}.description`)}
              </p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
