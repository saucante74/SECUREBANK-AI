import type { EvaluationMetrics, EvaluationRun } from "../api/types";

export type MetricDirection = "descriptive" | "higher" | "lower";
export type MetricFormat = "count" | "latency" | "percentage";
export type MetricGroup = "diversity" | "performance" | "ranking" | "relevance";

export interface DashboardMetric {
  direction: MetricDirection;
  field: keyof EvaluationMetrics;
  format: MetricFormat;
  group: MetricGroup;
  key: string;
}

export const metricGroups: MetricGroup[] = [
  "relevance",
  "ranking",
  "performance",
  "diversity",
];

export const dashboardMetrics: DashboardMetric[] = [
  { key: "precision1", field: "precision_at_1", group: "relevance", format: "percentage", direction: "higher" },
  { key: "precision3", field: "precision_at_3", group: "relevance", format: "percentage", direction: "higher" },
  { key: "recall1", field: "recall_at_1", group: "relevance", format: "percentage", direction: "higher" },
  { key: "recall3", field: "recall_at_3", group: "relevance", format: "percentage", direction: "higher" },
  { key: "f1_1", field: "f1_at_1", group: "relevance", format: "percentage", direction: "higher" },
  { key: "f1_3", field: "f1_at_3", group: "relevance", format: "percentage", direction: "higher" },
  { key: "map3", field: "map_at_3", group: "relevance", format: "percentage", direction: "higher" },
  { key: "success1", field: "success_at_1", group: "relevance", format: "percentage", direction: "higher" },
  { key: "success3", field: "success_at_3", group: "relevance", format: "percentage", direction: "higher" },
  { key: "mrr3", field: "mrr_at_3", group: "ranking", format: "percentage", direction: "higher" },
  { key: "ndcg3", field: "ndcg_at_3", group: "ranking", format: "percentage", direction: "higher" },
  { key: "source1", field: "source_hit_at_1", group: "ranking", format: "percentage", direction: "higher" },
  { key: "source3", field: "source_hit_at_3", group: "ranking", format: "percentage", direction: "higher" },
  { key: "evidence1", field: "evidence_hit_at_1", group: "ranking", format: "percentage", direction: "higher" },
  { key: "evidence3", field: "evidence_hit_at_3", group: "ranking", format: "percentage", direction: "higher" },
  { key: "meanLatency", field: "mean_latency_seconds", group: "performance", format: "latency", direction: "lower" },
  { key: "p50Latency", field: "latency_p50_seconds", group: "performance", format: "latency", direction: "lower" },
  { key: "p95Latency", field: "latency_p95_seconds", group: "performance", format: "latency", direction: "lower" },
  { key: "errorRate", field: "error_rate", group: "performance", format: "percentage", direction: "lower" },
  { key: "meanChunks", field: "mean_returned_chunk_count", group: "performance", format: "count", direction: "descriptive" },
  { key: "distinctDocuments3", field: "mean_distinct_document_count_at_3", group: "diversity", format: "count", direction: "descriptive" },
  { key: "sourceDiversity3", field: "mean_source_diversity_at_3", group: "diversity", format: "percentage", direction: "descriptive" },
];

function timestamp(run: EvaluationRun): number {
  const value = Date.parse(run.created_at);
  return Number.isNaN(value) ? Number.NEGATIVE_INFINITY : value;
}

export function sortEvaluationRuns(runs: EvaluationRun[]): EvaluationRun[] {
  return [...runs].sort((left, right) => {
    const dateDifference = timestamp(right) - timestamp(left);
    return dateDifference || right.run_id.localeCompare(left.run_id);
  });
}

const preferredEngines = ["BM25", "Qdrant", "RRF", "RRF + FlashRank"];

export function sortEngines(engines: string[]): string[] {
  return [...engines].sort((left, right) => {
    const leftIndex = preferredEngines.indexOf(left);
    const rightIndex = preferredEngines.indexOf(right);
    const normalizedLeft = leftIndex < 0 ? preferredEngines.length : leftIndex;
    const normalizedRight = rightIndex < 0 ? preferredEngines.length : rightIndex;
    return normalizedLeft - normalizedRight || left.localeCompare(right);
  });
}

export function defaultEngine(engines: string[]): string {
  return engines.includes("RRF") ? "RRF" : (engines[0] ?? "");
}
