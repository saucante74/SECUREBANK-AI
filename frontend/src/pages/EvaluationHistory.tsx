import { Fragment, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { compareEvaluationRuns } from "../api/services";
import type { ConfigurationValue, EvaluationComparison, EvaluationRun } from "../api/types";

interface EvaluationHistoryProps {
  runs: EvaluationRun[];
}

function displayValue(value: ConfigurationValue | undefined): string {
  return value === null || value === undefined ? "—" : String(value);
}

function configuration(run: EvaluationRun): string {
  return Object.entries(run.rag_configuration)
    .map(([name, value]) => `${name}=${displayValue(value)}`)
    .join(" · ") || "—";
}

export function EvaluationHistory({ runs }: EvaluationHistoryProps) {
  const { t, i18n } = useTranslation();
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const [previousId, setPreviousId] = useState(runs.at(1)?.run_id ?? runs[0].run_id);
  const [newId, setNewId] = useState(runs[0].run_id);
  const [comparison, setComparison] = useState<EvaluationComparison>();
  const [error, setError] = useState(false);
  const counts = useMemo(() => ({
    configurations: new Set(runs.map((run) => JSON.stringify(run.rag_configuration))).size,
    engines: new Set(runs.flatMap((run) => Object.keys(run.measured_metrics))).size,
  }), [runs]);

  const toggle = (runId: string) => {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(runId)) next.delete(runId);
      else next.add(runId);
      return next;
    });
  };

  const compare = async () => {
    setError(false);
    try {
      setComparison(await compareEvaluationRuns(previousId, newId));
    } catch {
      setError(true);
    }
  };

  return (
    <section className="border-t border-border pt-8" aria-labelledby="history-title">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 id="history-title" className="text-xl font-bold text-brand-navy">{t("evaluation.history.title")}</h2>
          <p className="mt-1 text-sm text-muted">{t("evaluation.history.description")}</p>
        </div>
        <dl className="flex flex-wrap gap-2 text-xs font-semibold text-muted">
          {[
            [t("evaluation.summary.runs"), runs.length],
            [t("evaluation.summary.configurations"), counts.configurations],
            [t("evaluation.summary.engines"), counts.engines],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-full bg-surface px-3 py-2">
              <dt className="inline">{label}: </dt>
              <dd className="inline text-brand-navy">{value}</dd>
            </div>
          ))}
        </dl>
      </div>
      <div className="mt-5 overflow-x-auto rounded-2xl border border-border bg-white shadow-soft">
        <table className="min-w-[64rem] text-left text-sm">
          <thead className="border-b border-border text-xs uppercase tracking-wide text-muted">
            <tr>
              {["details", "date", "run", "configuration", "engines", "source1", "source3", "evidence1", "evidence3", "latency"].map((key) => (
                <th key={key} className="whitespace-nowrap px-3 py-3">{t(`evaluation.history.${key}`)}</th>
              ))}
            </tr>
          </thead>
          {runs.map((run) => {
            const engines = Object.entries(run.measured_metrics);
            const isExpanded = expanded.has(run.run_id);
            const detailsId = `evaluation-run-${run.run_id}-engines`;
            return (
              <Fragment key={run.run_id}>
                <tbody>
                  <tr className="border-b border-border bg-surface/80 font-semibold text-brand-navy">
                    <td className="px-3 py-3">
                      <button
                        type="button"
                        className="inline-flex size-9 items-center justify-center rounded-lg border border-border bg-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                        aria-controls={detailsId}
                        aria-expanded={isExpanded}
                        aria-label={t(isExpanded ? "evaluation.history.collapse" : "evaluation.history.expand", { runId: run.run_id })}
                        onClick={() => {
                          toggle(run.run_id);
                        }}
                      >
                        <span aria-hidden="true">{isExpanded ? "▼" : "▶"}</span>
                      </button>
                    </td>
                    <td className="whitespace-nowrap px-3 py-3">
                      {new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium", timeStyle: "short" }).format(new Date(run.created_at))}
                    </td>
                    <td className="max-w-36 truncate px-3 py-3 font-mono" title={run.run_id}>{run.run_id}</td>
                    <td className="max-w-72 truncate px-3 py-3 font-normal text-muted" title={configuration(run)}>{configuration(run)}</td>
                    <td className="px-3 py-3 text-center">{engines.length}</td>
                    <td className="px-3 py-3 text-muted" colSpan={5}>—</td>
                  </tr>
                </tbody>
                <tbody id={detailsId}>
                  {isExpanded && engines.map(([engine, metrics]) => (
                    <tr key={`${run.run_id}-${engine}`} className="border-b border-border/70">
                      <td className="px-3 py-3" aria-hidden="true" />
                      <th scope="row" className="whitespace-nowrap px-3 py-3 pl-6 font-semibold" colSpan={4}>{engine}</th>
                      <td className="px-3 py-3">{metrics.source_hit_at_1.toFixed(3)}</td>
                      <td className="px-3 py-3">{metrics.source_hit_at_3.toFixed(3)}</td>
                      <td className="px-3 py-3">{metrics.evidence_hit_at_1.toFixed(3)}</td>
                      <td className="px-3 py-3">{metrics.evidence_hit_at_3.toFixed(3)}</td>
                      <td className="whitespace-nowrap px-3 py-3">{(metrics.mean_latency_seconds * 1000).toFixed(1)} ms</td>
                    </tr>
                  ))}
                </tbody>
              </Fragment>
            );
          })}
        </table>
      </div>

      <div className="mt-8 rounded-2xl border border-border bg-white p-5 shadow-soft">
        <h2 className="text-xl font-bold text-brand-navy">{t("evaluation.comparison.title")}</h2>
        {error && <p role="alert" className="mt-4 rounded-xl bg-red-50 p-4 text-red-800">{t("evaluation.comparison.error")}</p>}
        <div className="mt-4 flex flex-wrap items-end gap-4">
          {[
            { key: "previous", value: previousId, setter: setPreviousId },
            { key: "new", value: newId, setter: setNewId },
          ].map(({ key, value, setter }) => (
            <label key={key} className="grid gap-2 text-sm font-semibold">
              {t(`evaluation.comparison.${key}`)}
              <select className="rounded-lg border border-border bg-white px-3 py-2" value={value} onChange={(event) => { setter(event.target.value); }}>
                {runs.map((run) => <option key={run.run_id}>{run.run_id}</option>)}
              </select>
            </label>
          ))}
          <button type="button" className="rounded-lg bg-brand-navy px-5 py-2.5 text-sm font-bold text-white" onClick={() => void compare()}>
            {t("evaluation.comparison.action")}
          </button>
        </div>
        {comparison && (
          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <div>
              <h3 className="font-bold">{t("evaluation.comparison.configuration")}</h3>
              <ul className="mt-3 space-y-2 text-sm text-muted">
                {comparison.configuration_changes.length
                  ? comparison.configuration_changes.map((change) => <li key={change.name}>{change.name}: {displayValue(change.previous_value)} → {displayValue(change.new_value)}</li>)
                  : <li>{t("evaluation.comparison.noConfigurationChange")}</li>}
              </ul>
            </div>
            <div>
              <h3 className="font-bold">{t("evaluation.comparison.metrics")}</h3>
              <ul className="mt-3 max-h-64 space-y-2 overflow-auto text-sm text-muted">
                {comparison.metric_deltas.map((metric) => (
                  <li key={`${metric.engine}-${metric.metric}`}>
                    {metric.engine} · {t(`evaluation.metrics.${metric.metric}`)}: {metric.delta === null ? "—" : `${metric.delta >= 0 ? "+" : ""}${metric.delta.toFixed(3)}`}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
