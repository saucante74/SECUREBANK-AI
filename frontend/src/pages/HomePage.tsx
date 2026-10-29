import { useTranslation } from "react-i18next";

import { InfoCard } from "../components/InfoCard";

export function HomePage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-8 sm:space-y-10">
      <section aria-labelledby="welcome-title">
        <p className="text-sm font-semibold uppercase tracking-[0.14em] text-accent-strong">
          {t("home.eyebrow")}
        </p>
        <h1
          id="welcome-title"
          className="mt-4 max-w-4xl text-balance text-4xl font-extrabold leading-tight tracking-tight text-ink sm:text-5xl"
        >
          {t("home.title")}
        </h1>
        <p className="mt-5 max-w-3xl text-lg leading-8 text-muted">
          {t("home.description")}
        </p>
      </section>

      <section
        className="relative overflow-hidden rounded-3xl bg-brand-navy px-6 py-8 text-white shadow-panel sm:px-8 sm:py-10 lg:px-10"
        aria-labelledby="assistant-title"
      >
        <div className="absolute -right-20 -top-24 size-72 rounded-full bg-accent/15 blur-3xl" />
        <div className="relative max-w-3xl">
          <span className="inline-flex rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-accent">
            {t("home.assistantStatus")}
          </span>
          <h2 id="assistant-title" className="mt-5 text-2xl font-bold sm:text-3xl">
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

      <section className="rounded-3xl border border-border bg-white p-6 shadow-soft sm:p-8" aria-labelledby="future-title">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">
              {t("home.nextEyebrow")}
            </p>
            <h2 id="future-title" className="mt-2 text-xl font-semibold text-brand-navy">
              {t("home.nextTitle")}
            </h2>
          </div>
          <div
            className="flex flex-wrap gap-2"
            aria-label={t("accessibility.plannedFeatures")}
          >
            <span className="rounded-full border border-border bg-white px-3 py-1.5 text-sm font-medium text-muted">
              {t("home.backendConnection")}
            </span>
            <span className="rounded-full border border-border bg-white px-3 py-1.5 text-sm font-medium text-muted">
              {t("home.documentNavigation")}
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}
