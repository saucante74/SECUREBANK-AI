import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

const stepCount = 3;
const stepDurationMilliseconds = 1_400;

export function RagLoadingPanel() {
  const { t } = useTranslation();
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setActiveStep((currentStep) => {
        if (currentStep >= stepCount - 1) {
          window.clearInterval(interval);
          return currentStep;
        }
        return currentStep + 1;
      });
    }, stepDurationMilliseconds);

    return () => {
      window.clearInterval(interval);
    };
  }, []);

  const steps = [
    t("assistant.loader.analyzing"),
    t("assistant.loader.searching"),
    t("assistant.loader.preparing"),
  ];

  return (
    <section className="flex min-h-60 items-center rounded-2xl border border-border bg-white px-6 py-8 shadow-soft sm:px-8">
      <p className="sr-only" role="status" aria-live="polite">
        {t("assistant.loader.accessibleStatus")}
      </p>
      <div className="mx-auto w-full max-w-lg" aria-hidden="true">
        <div className="flex items-center gap-4">
          <span className="relative flex size-11 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent-strong">
            <span className="absolute inset-0 animate-ping rounded-xl bg-accent/15" />
            <svg className="relative size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 19.5V5a2 2 0 0 1 2-2h11a2 2 0 0 1 2 2v14.5" />
              <path d="M4 17h15M8 7h7M8 11h5" />
            </svg>
          </span>
          <div>
            <h2 className="text-lg font-bold text-ink">
              {t("assistant.loader.title")}
            </h2>
            <p className="mt-1 text-sm text-muted">
              {t("assistant.loader.description")}
            </p>
          </div>
        </div>
        <ol className="mt-7 space-y-4">
          {steps.map((step, index) => {
            const isActive = index === activeStep;
            const isComplete = index < activeStep;
            return (
              <li key={step} className="flex items-center gap-4">
                <span
                  className={`flex size-6 shrink-0 items-center justify-center rounded-full border transition-colors duration-300 ${
                    isActive
                      ? "border-accent bg-accent text-brand-navy shadow-[0_0_0_5px_rgb(49_217_160_/_0.12)]"
                      : isComplete
                        ? "border-accent-strong bg-accent-soft text-accent-strong"
                        : "border-border bg-surface text-muted"
                  }`}
                >
                  {isComplete ? (
                    <svg className="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="m5 12 4 4L19 6" />
                    </svg>
                  ) : (
                    <span className={`size-1.5 rounded-full ${isActive ? "animate-pulse bg-brand-navy" : "bg-muted/50"}`} />
                  )}
                </span>
                <span className={`text-sm transition-colors duration-300 ${isActive ? "font-semibold text-ink" : isComplete ? "text-accent-strong" : "text-muted"}`}>
                  {step}
                </span>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
