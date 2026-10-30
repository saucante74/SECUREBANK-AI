import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../api/client";
import { compareEvaluationRuns, getEvaluationRuns } from "../api/services";
import type {
  ConfigurationValue,
  EvaluationComparison,
  EvaluationRun,
} from "../api/types";

interface EvaluationPageProps {
  onSessionExpired: () => void;
}

function displayValue(value: ConfigurationValue | undefined): string {
  return value === null || value === undefined ? "—" : String(value);
}

function formatMetric(value: number): string {
  return value.toFixed(3);
}

export function EvaluationPage({ onSessionExpired }: EvaluationPageProps) {
  const { t, i18n } = useTranslation();
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [previousRunId, setPreviousRunId] = useState("");
  const [newRunId, setNewRunId] = useState("");
  const [comparison, setComparison] = useState<EvaluationComparison>();

  useEffect(() => {
    const controller = new AbortController();
    void getEvaluationRuns(undefined, controller.signal)
      .then((history) => {
        setRuns(history);
        setPreviousRunId(history.at(1)?.run_id ?? history.at(0)?.run_id ?? "");
        setNewRunId(history.at(0)?.run_id ?? "");
      })
      .catch((reason: unknown) => {
        if (reason instanceof ApiError && reason.category === "unauthenticated") {
          onSessionExpired();
        }
        if (!(reason instanceof ApiError && reason.category === "aborted")) {
          setError(true);
        }
      })
      .finally(() => {
        setLoading(false);
      });
    return () => {
      controller.abort();
    };
  }, [onSessionExpired]);

  const summary = useMemo(() => {
    const engines = runs.flatMap((run) => Object.values(run.measured_metrics));
    const configurations = new Set(
      runs.map((run) => JSON.stringify(run.rag_configuration)),
    ).size;
    const bestEvidence = engines.length
      ? Math.max(...engines.map((metrics) => metrics.evidence_hit_at_3))
      : undefined;
    const meanLatency = engines.length
      ? engines.reduce((total, metrics) => total + metrics.mean_latency_seconds, 0) /
        engines.length
      : undefined;
    return { configurations, bestEvidence, meanLatency };
  }, [runs]);

  const compare = async () => {
    if (!previousRunId || !newRunId) return;
    setError(false);
    try {
      setComparison(await compareEvaluationRuns(previousRunId, newRunId));
    } catch (reason: unknown) {
      if (reason instanceof ApiError && reason.category === "unauthenticated") {
        onSessionExpired();
      }
      setError(true);
    }
  };

  if (loading) {
    return <p role="status">{t("evaluation.loading")}</p>;
  }

  return (
    <div className="space-y-8">
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

      {error && <p role="alert" className="rounded-xl bg-red-50 p-4 text-red-800">{t("evaluation.error")}</p>}

      <section aria-label={t("evaluation.summary.title")} className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          [t("evaluation.summary.runs"), String(runs.length)],
          [t("evaluation.summary.configurations"), String(summary.configurations)],
          [t("evaluation.summary.bestEvidence"), summary.bestEvidence === undefined ? "—" : formatMetric(summary.bestEvidence)],
          [t("evaluation.summary.meanLatency"), summary.meanLatency === undefined ? "—" : `${(summary.meanLatency * 1000).toFixed(1)} ms`],
        ].map(([label, value]) => (
          <article key={label} className="rounded-2xl border border-border bg-white p-5 shadow-soft">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
            <p className="mt-2 text-2xl font-extrabold text-brand-navy">{value}</p>
          </article>
        ))}
      </section>

      <section className="rounded-2xl border border-border bg-white p-5 shadow-soft">
        <h2 className="text-xl font-bold text-brand-navy">{t("evaluation.history.title")}</h2>
        {runs.length === 0 ? (
          <p className="mt-4 text-muted">{t("evaluation.empty")}</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-border text-xs uppercase tracking-wide text-muted">
                <tr>{["date", "run", "commit", "engine", "variable", "previous", "new", "source1", "source3", "evidence1", "evidence3", "latency"].map((key) => <th key={key} className="whitespace-nowrap px-3 py-3">{t(`evaluation.history.${key}`)}</th>)}</tr>
              </thead>
              <tbody>
                {runs.flatMap((run) => Object.entries(run.measured_metrics).map(([engine, metrics]) => (
                  <tr key={`${run.run_id}-${engine}`} className="border-b border-border/70">
                    <td className="whitespace-nowrap px-3 py-3">{new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium", timeStyle: "short" }).format(new Date(run.created_at))}</td>
                    <td className="max-w-32 truncate px-3 py-3 font-mono" title={run.run_id}>{run.run_id}</td>
                    <td className="font-mono px-3 py-3">{run.code_version.slice(0, 8)}</td>
                    <td className="whitespace-nowrap px-3 py-3 font-semibold">{engine}</td>
                    <td className="px-3 py-3">{run.parameter_change?.name ?? "—"}</td>
                    <td className="px-3 py-3">{displayValue(run.parameter_change?.previous_value)}</td>
                    <td className="px-3 py-3">{displayValue(run.parameter_change?.new_value)}</td>
                    <td className="px-3 py-3">{formatMetric(metrics.source_hit_at_1)}</td>
                    <td className="px-3 py-3">{formatMetric(metrics.source_hit_at_3)}</td>
                    <td className="px-3 py-3">{formatMetric(metrics.evidence_hit_at_1)}</td>
                    <td className="px-3 py-3">{formatMetric(metrics.evidence_hit_at_3)}</td>
                    <td className="whitespace-nowrap px-3 py-3">{(metrics.mean_latency_seconds * 1000).toFixed(1)} ms</td>
                  </tr>
                )))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-border bg-white p-5 shadow-soft">
        <h2 className="text-xl font-bold text-brand-navy">{t("evaluation.comparison.title")}</h2>
        <div className="mt-4 flex flex-wrap items-end gap-4">
          {[
            { key: "previous", value: previousRunId, setter: setPreviousRunId },
            { key: "new", value: newRunId, setter: setNewRunId },
          ].map(({ key, value, setter }) => (
            <label key={key} className="grid gap-2 text-sm font-semibold">
              {t(`evaluation.comparison.${key}`)}
              <select className="rounded-lg border border-border bg-white px-3 py-2" value={value} onChange={(event) => {
                setter(event.target.value);
              }}>
                {runs.map((run) => <option key={run.run_id} value={run.run_id}>{run.run_id}</option>)}
              </select>
            </label>
          ))}
          <button type="button" className="rounded-lg bg-brand-navy px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50" disabled={!runs.length} onClick={() => void compare()}>{t("evaluation.comparison.action")}</button>
        </div>
        {comparison && (
          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <div>
              <h3 className="font-bold">{t("evaluation.comparison.configuration")}</h3>
              <ul className="mt-3 space-y-2 text-sm text-muted">
                {comparison.configuration_changes.length ? comparison.configuration_changes.map((change) => <li key={change.name}>{change.name}: {displayValue(change.previous_value)} → {displayValue(change.new_value)}</li>) : <li>{t("evaluation.comparison.noConfigurationChange")}</li>}
              </ul>
            </div>
            <div>
              <h3 className="font-bold">{t("evaluation.comparison.metrics")}</h3>
              <ul className="mt-3 max-h-64 space-y-2 overflow-auto text-sm text-muted">
                {comparison.metric_deltas.map((metric) => <li key={`${metric.engine}-${metric.metric}`}>{metric.engine} · {t(`evaluation.metrics.${metric.metric}`)}: {metric.delta === null ? "—" : `${metric.delta >= 0 ? "+" : ""}${metric.delta.toFixed(3)}`}</li>)}
              </ul>
            </div>
          </div>
        )}
      </section>

      <details className="rounded-2xl border border-border bg-accent-soft p-5">
        <summary className="cursor-pointer font-bold text-brand-navy">{t("evaluation.guide.title")}</summary>
        <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
          {["baseline", "bm25", "qdrant", "rrf", "flashrank", "source", "evidence", "latency", "difference"].map((key) => <div key={key}><dt className="font-bold text-brand-navy">{t(`evaluation.guide.${key}.title`)}</dt><dd className="mt-1 leading-6 text-muted">{t(`evaluation.guide.${key}.description`)}</dd></div>)}
        </dl>
      </details>
    </div>
  );
}
