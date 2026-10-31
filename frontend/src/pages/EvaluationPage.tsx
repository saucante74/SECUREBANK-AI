import { Fragment, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../api/client";
import { compareEvaluationRuns, getEvaluationRuns } from "../api/services";
import type {
  ConfigurationValue,
  EvaluationComparison,
  EvaluationRun,
} from "../api/types";

function displayValue(value: ConfigurationValue | undefined): string {
  return value === null || value === undefined ? "—" : String(value);
}

function formatMetric(value: number): string {
  return value.toFixed(3);
}

function configurationSummary(run: EvaluationRun): string {
  if (run.parameter_change) {
    return `${run.parameter_change.name}: ${displayValue(run.parameter_change.previous_value)} → ${displayValue(run.parameter_change.new_value)}`;
  }
  const entries = Object.entries(run.rag_configuration);
  const visibleEntries = entries
    .slice(0, 2)
    .map(([name, value]) => `${name}=${displayValue(value)}`);
  const remainingEntries = entries.length - visibleEntries.length;
  const summary = [
    ...visibleEntries,
    ...(remainingEntries > 0 ? [`+${String(remainingEntries)}`] : []),
  ].join(" · ");
  return summary || "—";
}

function fullConfiguration(run: EvaluationRun): string {
  return Object.entries(run.rag_configuration)
    .map(([name, value]) => `${name}=${displayValue(value)}`)
    .join(" · ");
}

export function EvaluationPage() {
  const { t, i18n } = useTranslation();
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [previousRunId, setPreviousRunId] = useState("");
  const [newRunId, setNewRunId] = useState("");
  const [comparison, setComparison] = useState<EvaluationComparison>();
  const [expandedRunIds, setExpandedRunIds] = useState<Set<string>>(
    () => new Set(),
  );

  useEffect(() => {
    const controller = new AbortController();
    void getEvaluationRuns(undefined, controller.signal)
      .then((history) => {
        setRuns(history);
        setPreviousRunId(history.at(1)?.run_id ?? history.at(0)?.run_id ?? "");
        setNewRunId(history.at(0)?.run_id ?? "");
      })
      .catch((reason: unknown) => {
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
  }, []);

  const summary = useMemo(() => {
    const engines = runs.flatMap((run) => Object.values(run.measured_metrics));
    const engineNames = new Set(
      runs.flatMap((run) => Object.keys(run.measured_metrics)),
    );
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
    return {
      configurations,
      engines: engineNames.size,
      bestEvidence,
      meanLatency,
    };
  }, [runs]);

  const toggleRun = (runId: string) => {
    setExpandedRunIds((current) => {
      const next = new Set(current);
      if (next.has(runId)) {
        next.delete(runId);
      } else {
        next.add(runId);
      }
      return next;
    });
  };

  const compare = async () => {
    if (!previousRunId || !newRunId) return;
    setError(false);
    try {
      setComparison(await compareEvaluationRuns(previousRunId, newRunId));
    } catch {
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

      <section aria-label={t("evaluation.summary.title")} className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {[
          [t("evaluation.summary.runs"), String(runs.length)],
          [t("evaluation.summary.configurations"), String(summary.configurations)],
          [t("evaluation.summary.engines"), String(summary.engines)],
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
            <table className="min-w-[64rem] text-left text-sm">
              <thead className="border-b border-border text-xs uppercase tracking-wide text-muted">
                <tr>{["details", "date", "run", "configuration", "engines", "source1", "source3", "evidence1", "evidence3", "latency"].map((key) => <th key={key} className="whitespace-nowrap px-3 py-3">{t(`evaluation.history.${key}`)}</th>)}</tr>
              </thead>
              {runs.map((run) => {
                const engines = Object.entries(run.measured_metrics);
                const isExpanded = expandedRunIds.has(run.run_id);
                const detailsId = `evaluation-run-${run.run_id}-engines`;
                return (
                  <Fragment key={run.run_id}>
                    <tbody>
                      <tr className="border-b border-border bg-surface/80 font-semibold text-brand-navy transition-colors hover:bg-accent-soft/60">
                        <td className="px-3 py-3">
                          <button
                            type="button"
                            className="inline-flex size-9 items-center justify-center rounded-lg border border-border bg-white text-sm transition-colors hover:border-accent/50 hover:text-accent-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                            aria-controls={detailsId}
                            aria-expanded={isExpanded}
                            aria-label={t(
                              isExpanded
                                ? "evaluation.history.collapse"
                                : "evaluation.history.expand",
                              { runId: run.run_id },
                            )}
                            onClick={() => {
                              toggleRun(run.run_id);
                            }}
                          >
                            <span aria-hidden="true">{isExpanded ? "▼" : "▶"}</span>
                          </button>
                        </td>
                        <td className="whitespace-nowrap px-3 py-3">
                          {new Intl.DateTimeFormat(i18n.language, {
                            dateStyle: "medium",
                            timeStyle: "short",
                          }).format(new Date(run.created_at))}
                        </td>
                        <td className="max-w-36 truncate px-3 py-3 font-mono" title={run.run_id}>
                          {run.run_id}
                        </td>
                        <td className="max-w-72 truncate px-3 py-3 font-normal text-muted" title={fullConfiguration(run)}>
                          {configurationSummary(run)}
                        </td>
                        <td className="px-3 py-3 text-center">{engines.length}</td>
                        <td className="px-3 py-3 text-muted" colSpan={5}>—</td>
                      </tr>
                    </tbody>
                    <tbody id={detailsId}>
                      {isExpanded &&
                        engines.map(([engine, metrics]) => (
                          <tr key={`${run.run_id}-${engine}`} className="border-b border-border/70 bg-white transition-colors hover:bg-surface/70">
                            <td className="px-3 py-3" aria-hidden="true" />
                            <th scope="row" className="whitespace-nowrap px-3 py-3 pl-6 font-semibold text-ink" colSpan={4}>
                              {engine}
                            </th>
                            <td className="px-3 py-3">{formatMetric(metrics.source_hit_at_1)}</td>
                            <td className="px-3 py-3">{formatMetric(metrics.source_hit_at_3)}</td>
                            <td className="px-3 py-3">{formatMetric(metrics.evidence_hit_at_1)}</td>
                            <td className="px-3 py-3">{formatMetric(metrics.evidence_hit_at_3)}</td>
                            <td className="whitespace-nowrap px-3 py-3">{(metrics.mean_latency_seconds * 1000).toFixed(1)} ms</td>
                          </tr>
                        ))}
                    </tbody>
                  </Fragment>
                );
              })}
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
