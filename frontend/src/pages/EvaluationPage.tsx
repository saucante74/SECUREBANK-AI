import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../api/client";
import { getEvaluationRuns } from "../api/services";
import type {
  EvaluationIRMetricName,
  EvaluationMetrics,
  EvaluationRun,
} from "../api/types";
import { MetricCard } from "../components/MetricCard";
import {
  dashboardMetrics,
  defaultEngine,
  metricBelongsToTab,
  metricGroups,
  metricTabs,
  sortEngines,
  sortEvaluationRuns,
  type DashboardMetric,
  type MetricTab,
} from "./evaluationDashboard";
import { EvaluationHistory } from "./EvaluationHistory";

function displayConfiguration(run: EvaluationRun): string {
  const entries = Object.entries(run.rag_configuration);
  if (!entries.length) return "—";
  const visible = entries.slice(0, 2).map(([name, value]) => `${name}=${String(value)}`);
  const remaining = entries.length - visible.length;
  return [...visible, ...(remaining ? [`+${String(remaining)}`] : [])].join(" · ");
}

function formatValue(
  value: number | null | undefined,
  metric: DashboardMetric,
  language: string,
  unavailable: string,
): { unit?: string; value: string } {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return { value: unavailable };
  }
  if (metric.format === "percentage") {
    return {
      value: new Intl.NumberFormat(language, {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      }).format(value * 100),
      unit: "%",
    };
  }
  if (metric.format === "latency") {
    return {
      value: new Intl.NumberFormat(language, {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      }).format(value * 1000),
      unit: "ms",
    };
  }
  return {
    value: new Intl.NumberFormat(language, { maximumFractionDigits: 1 }).format(value),
  };
}

export function EvaluationPage() {
  const { t, i18n } = useTranslation();
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [selectedEngine, setSelectedEngine] = useState("");
  const [activeTab, setActiveTab] = useState<MetricTab>("relevance");
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    void getEvaluationRuns(undefined, controller.signal)
      .then((history) => {
        setRuns(sortEvaluationRuns(history));
      })
      .catch((reason: unknown) => {
        if (!(reason instanceof ApiError && reason.category === "aborted")) setError(true);
      })
      .finally(() => {
        setLoading(false);
      });
    return () => {
      controller.abort();
    };
  }, []);

  const latestRun = runs.at(0);
  const engines = useMemo(
    () => sortEngines(Object.keys(latestRun?.measured_metrics ?? {})),
    [latestRun],
  );
  const activeEngine = engines.includes(selectedEngine)
    ? selectedEngine
    : defaultEngine(engines);
  const metrics: EvaluationMetrics | undefined = latestRun?.measured_metrics[activeEngine];
  const irMetrics = latestRun?.ir_metrics[activeEngine];
  const qwenQuestionCount = irMetrics
    ? irMetrics.precision_at_1.evaluated_question_count
      + irMetrics.precision_at_1.unavailable_question_count
    : undefined;
  const visibleMetrics = dashboardMetrics.filter((metric) => (
    metricBelongsToTab(metric, activeTab)
  ));

  const selectTabFromKeyboard = (
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) => {
    let nextIndex: number | undefined;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % metricTabs.length;
    if (event.key === "ArrowLeft") nextIndex = (index - 1 + metricTabs.length) % metricTabs.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = metricTabs.length - 1;
    if (nextIndex === undefined) return;
    event.preventDefault();
    const nextTab = metricTabs[nextIndex];
    setActiveTab(nextTab);
    tabRefs.current[nextIndex]?.focus();
  };

  return (
    <div className="space-y-8">
      <h1 className="sr-only">{t("evaluation.title")}</h1>
      {loading && <p role="status">{t("evaluation.loading")}</p>}
      {error && <p role="alert" className="rounded-xl bg-red-50 p-4 text-red-800">{t("evaluation.error")}</p>}
      {!loading && !error && !latestRun && (
        <p className="rounded-2xl border border-border bg-white p-6 text-muted shadow-soft">
          {t("evaluation.empty")}
        </p>
      )}

      {latestRun && (
        <>
          <section className="grid gap-5 lg:grid-cols-[minmax(0,3fr)_minmax(17rem,2fr)]">
            <div aria-labelledby="latest-title" className="rounded-3xl bg-brand-navy p-6 text-white shadow-soft sm:p-8">
              <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-accent">
                <span className="size-2 rounded-full bg-accent" aria-hidden="true" />
                {t("evaluation.latest.eyebrow")}
              </p>
              <h2 id="latest-title" className="mt-4 font-display text-3xl font-extrabold leading-tight">
                {t("evaluation.latest.title")}
              </h2>
              <p className="mt-4 max-w-xl text-sm leading-6 text-white/60">
                {t("evaluation.description")}
              </p>
              <dl className="mt-8 grid gap-x-6 gap-y-5 sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-white/45">{t("evaluation.latest.run")}</dt>
                  <dd className="mt-2 break-all font-mono text-sm font-semibold text-white/75">{latestRun.run_id}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-white/45">{t("evaluation.latest.date")}</dt>
                  <dd className="mt-2 font-bold">
                    {new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium", timeStyle: "short" }).format(new Date(latestRun.created_at))}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-white/45">{t("evaluation.latest.engines")}</dt>
                  <dd className="mt-2 font-display text-2xl font-extrabold">{engines.length}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-white/45">{t("evaluation.latest.configuration")}</dt>
                  <dd className="mt-2 text-sm font-semibold text-white/70">{displayConfiguration(latestRun)}</dd>
                </div>
              </dl>
            </div>

            <div className="flex flex-col rounded-3xl border border-border bg-white p-6 shadow-soft" aria-labelledby="engine-title">
              <h2 id="engine-title" className="text-xs font-bold uppercase tracking-[0.14em] text-muted">
                {t("evaluation.dashboard.engineLabel")}
              </h2>
              <label className="mt-5 grid gap-2 text-sm font-semibold text-brand-navy">
                <span className="sr-only">{t("evaluation.dashboard.engineLabel")}</span>
                <select
                  className="w-full rounded-xl border border-border bg-surface/50 px-4 py-3.5 font-bold shadow-soft focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                  value={activeEngine}
                  onChange={(event) => {
                    setSelectedEngine(event.target.value);
                  }}
                >
                  {engines.map((engine) => <option key={engine}>{engine}</option>)}
                </select>
              </label>
              <p className="mt-5 text-sm leading-6 text-muted">
                {t("evaluation.dashboard.engineDescription")}
              </p>
              {irMetrics?.judgment_source === "qwen" && qwenQuestionCount !== undefined && (
                <p className="mt-auto flex gap-3 rounded-2xl border border-accent/20 bg-accent-soft p-4 text-sm font-semibold leading-5 text-accent-strong lg:mt-8">
                  <span className="flex size-5 shrink-0 items-center justify-center rounded-full border-2 border-current text-xs" aria-hidden="true">i</span>
                  {t("evaluation.dashboard.qwenSummary", { count: qwenQuestionCount })}
                </p>
              )}
            </div>
          </section>

          <section aria-label={t("evaluation.dashboard.metricsTitle")}>
            <div
              className="grid grid-cols-1 gap-1 rounded-2xl bg-border/50 p-1 sm:grid-cols-3"
              role="tablist"
              aria-label={t("evaluation.dashboard.metricsTitle")}
            >
              {metricTabs.map((tab, index) => {
                const isActive = tab === activeTab;
                return (
                  <button
                    key={tab}
                    ref={(element) => {
                      tabRefs.current[index] = element;
                    }}
                    id={`evaluation-tab-${tab}`}
                    type="button"
                    role="tab"
                    aria-controls="evaluation-metric-panel"
                    aria-selected={isActive}
                    tabIndex={isActive ? 0 : -1}
                    className={`rounded-xl px-4 py-3 text-sm font-bold transition-colors ${isActive ? "bg-white text-brand-navy shadow-soft" : "text-muted hover:bg-white/50 hover:text-brand-navy"}`}
                    onClick={() => {
                      setActiveTab(tab);
                    }}
                    onKeyDown={(event) => {
                      selectTabFromKeyboard(event, index);
                    }}
                  >
                    {t(`evaluation.metricTabs.${tab}`)}
                  </button>
                );
              })}
            </div>

            <div
              id="evaluation-metric-panel"
              role="tabpanel"
              aria-labelledby={`evaluation-tab-${activeTab}`}
              className="mt-5 grid gap-5 md:grid-cols-2"
            >
              {visibleMetrics.map((metric) => {
                const irMetric = metric.source === "ir"
                  ? irMetrics?.[metric.field as EvaluationIRMetricName]
                  : undefined;
                const metricValue = metric.source === "ir"
                  ? irMetric?.value
                  : metrics?.[metric.field as keyof EvaluationMetrics];
                const formatted = formatValue(
                  metricValue,
                  metric,
                  i18n.language,
                  t("evaluation.dashboard.unavailable"),
                );
                const progress = metric.format === "percentage"
                  ? typeof metricValue === "number" && Number.isFinite(metricValue)
                    ? metricValue
                    : null
                  : undefined;
                return (
                  <MetricCard
                    key={metric.key}
                    name={t(`evaluation.metricCards.${metric.key}.name`)}
                    description={t(`evaluation.metricCards.${metric.key}.description`)}
                    details={irMetric ? [
                      t("evaluation.dashboard.questionAvailability", {
                        evaluated: irMetric.evaluated_question_count,
                        unavailable: irMetric.unavailable_question_count,
                      }),
                    ] : undefined}
                    direction={t(`evaluation.directions.${metric.direction}`)}
                    progress={progress}
                    value={formatted.value}
                    unit={formatted.unit}
                  />
                );
              })}
            </div>
          </section>

          <section aria-labelledby="guide-title" className="rounded-3xl border border-accent/20 bg-accent-soft p-6 sm:p-8">
            <h2 id="guide-title" className="text-xl font-bold text-brand-navy">{t("evaluation.guide.title")}</h2>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-muted">{t("evaluation.guide.introduction")}</p>
            <div className="mt-5 space-y-3">
              {metricGroups.map((group) => (
                <details key={group} className="rounded-xl border border-border bg-white p-4">
                  <summary className="cursor-pointer font-bold text-brand-navy focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
                    {t(`evaluation.groups.${group}.title`)}
                  </summary>
                  <dl className="mt-4 grid gap-4 md:grid-cols-2">
                    {dashboardMetrics.filter((metric) => metric.group === group).map((metric) => (
                      <div key={metric.key}>
                        <dt className="font-bold text-brand-navy">{t(`evaluation.metricCards.${metric.key}.name`)}</dt>
                        <dd className="mt-1 text-sm leading-6 text-muted">
                          {t(`evaluation.metricCards.${metric.key}.description`)} {t(`evaluation.directions.${metric.direction}`)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                  <p className="mt-5 rounded-lg bg-surface p-3 text-sm leading-6 text-muted">
                    {t(`evaluation.guide.limitations.${group}`)}
                  </p>
                </details>
              ))}
            </div>
          </section>

          <EvaluationHistory runs={runs} />
        </>
      )}
    </div>
  );
}
