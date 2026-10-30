import { useTranslation } from "react-i18next";

const serviceSteps = ["question", "search", "answer", "sources"] as const;
const faqItems = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"] as const;

export function AboutPage() {
  const { t } = useTranslation();

  return (
    <div className="space-y-7">
      <section aria-labelledby="about-title">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent-strong">
          {t("about.eyebrow")}
        </p>
        <h1
          id="about-title"
          className="mt-2 font-display text-3xl font-extrabold tracking-tight text-ink sm:text-4xl"
        >
          {t("about.title")}
        </h1>
        <div className="mt-5 space-y-3 rounded-2xl border border-border bg-white p-5 text-base leading-7 text-muted shadow-soft sm:p-6">
          <p>{t("about.introduction.first")}</p>
          <p>{t("about.introduction.second")}</p>
          <p>{t("about.introduction.third")}</p>
          <p className="font-medium text-brand-navy">
            {t("about.introduction.disclaimer")}
          </p>
        </div>
      </section>

      <section aria-labelledby="service-operation-title">
        <h2
          id="service-operation-title"
          className="font-display text-xl font-bold text-brand-navy"
        >
          {t("about.operation.title")}
        </h2>
        <ol className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {serviceSteps.map((step, index) => (
            <li
              key={step}
              className="rounded-xl border border-border bg-white p-4 shadow-soft"
            >
              <span className="flex size-8 items-center justify-center rounded-lg bg-accent-soft text-sm font-bold text-accent-strong">
                {index + 1}
              </span>
              <p className="mt-3 text-sm leading-6 text-muted">
                {t(`about.operation.${step}`)}
              </p>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="faq-title">
        <h2 id="faq-title" className="font-display text-xl font-bold text-brand-navy">
          {t("about.faq.title")}
        </h2>
        <div className="mt-4 space-y-2">
          {faqItems.map((item) => (
            <details
              key={item}
              className="group rounded-xl border border-border bg-white shadow-soft"
            >
              <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-4 rounded-xl px-4 py-3 text-sm font-semibold text-brand-navy transition-colors hover:bg-surface focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
                <span>{t(`about.faq.items.${item}.question`)}</span>
                <svg
                  aria-hidden="true"
                  className="size-4 shrink-0 transition-transform group-open:rotate-180"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="m6 9 6 6 6-6" />
                </svg>
              </summary>
              <p className="border-t border-border px-4 py-4 text-sm leading-6 text-muted">
                {t(`about.faq.items.${item}.answer`)}
              </p>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}
