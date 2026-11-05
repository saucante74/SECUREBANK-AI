import snapshotData from "../data/evaluationSnapshot.json";
import type {
  EvaluationIRMetricName,
  EvaluationMetrics,
  EvaluationRun,
} from "../api/types";
import { sortEvaluationRuns } from "./evaluationDashboard";

export type EvaluationDataSource = "reference" | "synchronized";

export interface EvaluationDataSelection {
  runs: EvaluationRun[];
  source: EvaluationDataSource;
}

export const expectedEngines = [
  "BM25",
  "Qdrant",
  "RRF",
  "RRF + FlashRank",
] as const;

const measuredMetricNames: (keyof EvaluationMetrics)[] = [
  "source_hit_at_1",
  "source_hit_at_3",
  "evidence_hit_at_1",
  "evidence_hit_at_3",
  "mean_latency_seconds",
  "latency_p50_seconds",
  "latency_p95_seconds",
  "error_rate",
  "mean_returned_chunk_count",
  "mean_distinct_document_count_at_3",
  "mean_source_diversity_at_3",
];

const irMetricNames: EvaluationIRMetricName[] = [
  "precision_at_1",
  "precision_at_3",
  "recall_at_1",
  "recall_at_3",
  "f1_at_1",
  "f1_at_3",
  "map_at_3",
  "success_at_1",
  "success_at_3",
  "mrr_at_3",
  "ndcg_at_3",
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isMetricValue(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value));
}

function isMeasuredMetrics(value: unknown): boolean {
  return isRecord(value)
    && measuredMetricNames.every((name) => isMetricValue(value[name]));
}

function isIrMetric(value: unknown): boolean {
  return isRecord(value)
    && isMetricValue(value.value)
    && Number.isInteger(value.evaluated_question_count)
    && Number(value.evaluated_question_count) >= 0
    && Number.isInteger(value.unavailable_question_count)
    && Number(value.unavailable_question_count) >= 0;
}

function isIrMetrics(value: unknown): boolean {
  return isRecord(value)
    && value.judgment_source === "qwen"
    && irMetricNames.every((name) => isIrMetric(value[name]));
}

function isEvaluationRun(value: unknown): value is EvaluationRun {
  if (!isRecord(value) || typeof value.run_id !== "string") return false;
  if (typeof value.created_at !== "string" || Number.isNaN(Date.parse(value.created_at))) {
    return false;
  }
  if (!isRecord(value.rag_configuration) || !isRecord(value.measured_metrics)) {
    return false;
  }
  if (!isRecord(value.ir_metrics)) return false;
  const measuredMetrics = value.measured_metrics;
  const irMetrics = value.ir_metrics;
  if (!expectedEngines.every((engine) => isMeasuredMetrics(measuredMetrics[engine]))) {
    return false;
  }
  return Object.values(irMetrics).every(isIrMetrics);
}

export function isEvaluationRunList(value: unknown): value is EvaluationRun[] {
  return Array.isArray(value) && value.length > 0 && value.every(isEvaluationRun);
}

function validEvaluationRuns(value: unknown): EvaluationRun[] {
  return Array.isArray(value) ? value.filter(isEvaluationRun) : [];
}

function hasCompleteDashboardMetrics(run: EvaluationRun): boolean {
  return expectedEngines.every((engine) => isIrMetrics(run.ir_metrics[engine]));
}

export const referenceEvaluationRuns: EvaluationRun[] = isEvaluationRunList(
  snapshotData,
)
  ? sortEvaluationRuns(snapshotData)
  : [];

export function synchronizeEvaluationRuns(
  referenceRuns: EvaluationRun[],
  apiResponse: unknown,
): EvaluationDataSelection {
  if (!isEvaluationRunList(apiResponse)) {
    return { runs: referenceRuns, source: "reference" };
  }
  const apiRuns = sortEvaluationRuns(apiResponse);
  const apiLatest = apiRuns[0];
  const referenceLatest = referenceRuns.at(0);
  if (!hasCompleteDashboardMetrics(apiLatest)) {
    return { runs: referenceRuns, source: "reference" };
  }
  if (
    referenceLatest
    && Date.parse(apiLatest.created_at) <= Date.parse(referenceLatest.created_at)
  ) {
    return { runs: referenceRuns, source: "reference" };
  }
  return { runs: apiRuns, source: "synchronized" };
}

export function mergeEvaluationHistory(
  currentRuns: EvaluationRun[],
  apiResponse: unknown,
): EvaluationRun[] {
  const apiRuns = validEvaluationRuns(apiResponse);
  if (!apiRuns.length) return currentRuns;
  const runsById = new Map<string, EvaluationRun>();
  for (const run of [...currentRuns, ...apiRuns]) {
    if (!runsById.has(run.run_id)) runsById.set(run.run_id, run);
  }
  return sortEvaluationRuns([...runsById.values()]);
}
