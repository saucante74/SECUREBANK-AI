import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../api/client";
import { getEvaluationRuns } from "../api/services";
import type { EvaluationMetrics, EvaluationRun } from "../api/types";
import { MetricCard } from "../components/MetricCard";
import {
  dashboardMetrics,
  defaultEngine,
  metricGroups,
  sortEngines,
  sortEvaluationRuns,
  type DashboardMetric,
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
  value: number | undefined,
  metric: DashboardMetric,
  language: string,
  unavailable: string,
): { unit?: string; value: string } {
  if (value === undefined || !Number.isFinite(value)) return { value: unavailable };
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

  return (
    <div className="space-y-10">
      <section>
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent-strong">
          {t("evaluation.eyebrow")}
        </p>
        <h1 className="mt-2 text-3xl font-extrabold text-brand-navy">
          {t("evaluation.title")}
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-muted">
          {t("evaluation.description")}
        </p>
      </section>

      {loading && <p role="status">{t("evaluation.loading")}</p>}
      {error && <p role="alert" className="rounded-xl bg-red-50 p-4 text-red-800">{t("evaluation.error")}</p>}
      {!loading && !error && !latestRun && (
        <p className="rounded-2xl border border-border bg-white p-6 text-muted shadow-soft">
          {t("evaluation.empty")}
        </p>
      )}

      {latestRun && (
        <>
          <section aria-labelledby="latest-title" className="rounded-3xl bg-brand-navy p-6 text-white shadow-soft sm:p-8">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent">
              {t("evaluation.latest.eyebrow")}
            </p>
            <h2 id="latest-title" className="mt-2 text-2xl font-extrabold">
              {t("evaluation.latest.title")}
            </h2>
            <dl className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <dt className="text-xs font-semibold uppercase text-white/60">{t("evaluation.latest.run")}</dt>
                <dd className="mt-2 break-all font-mono text-sm font-bold">{latestRun.run_id}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase text-white/60">{t("evaluation.latest.date")}</dt>
                <dd className="mt-2 font-bold">
                  {new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium", timeStyle: "short" }).format(new Date(latestRun.created_at))}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase text-white/60">{t("evaluation.latest.engines")}</dt>
                <dd className="mt-2 text-2xl font-extrabold">{engines.length}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase text-white/60">{t("evaluation.latest.configuration")}</dt>
                <dd className="mt-2 text-sm font-bold">{displayConfiguration(latestRun)}</dd>
              </div>
            </dl>
          </section>

          <section aria-labelledby="engine-title">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h2 id="engine-title" className="text-xl font-bold text-brand-navy">
                  {t("evaluation.dashboard.engineTitle")}
                </h2>
                <p className="mt-1 text-sm text-muted">{t("evaluation.dashboard.engineDescription")}</p>
              </div>
              <label className="grid gap-2 text-sm font-semibold text-brand-navy">
                {t("evaluation.dashboard.engineLabel")}
                <select
                  className="min-w-52 rounded-xl border border-border bg-white px-4 py-3 shadow-soft focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                  value={activeEngine}
                  onChange={(event) => {
                    setSelectedEngine(event.target.value);
                  }}
                >
                  {engines.map((engine) => <option key={engine}>{engine}</option>)}
                </select>
              </label>
            </div>
          </section>

          <section aria-label={t("evaluation.dashboard.metricsTitle")} className="space-y-10">
            {metricGroups.map((group) => (
              <div key={group}>
                <h2 className="text-xl font-bold text-brand-navy">{t(`evaluation.groups.${group}.title`)}</h2>
                <p className="mt-1 text-sm text-muted">{t(`evaluation.groups.${group}.description`)}</p>
                <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  {dashboardMetrics.filter((metric) => metric.group === group).map((metric) => {
                    const formatted = formatValue(
                      metrics?.[metric.field],
                      metric,
                      i18n.language,
                      t("evaluation.dashboard.unavailable"),
                    );
                    return (
                      <MetricCard
                        key={metric.key}
                        name={t(`evaluation.metricCards.${metric.key}.name`)}
                        description={t(`evaluation.metricCards.${metric.key}.description`)}
                        direction={t(`evaluation.directions.${metric.direction}`)}
                        value={formatted.value}
                        unit={formatted.unit}
                      />
                    );
                  })}
                </div>
              </div>
            ))}
          </section>

          <section aria-labelledby="guide-title" className="rounded-2xl border border-border bg-accent-soft p-5">
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
