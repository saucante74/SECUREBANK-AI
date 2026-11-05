import { describe, expect, it } from "vitest";

import type { EvaluationRun } from "../api/types";
import { dashboardMetrics } from "./evaluationDashboard";
import {
  expectedEngines,
  isEvaluationRunList,
  referenceEvaluationRuns,
  synchronizeEvaluationRuns,
} from "./evaluationData";

const referenceRun = referenceEvaluationRuns[0];

function cloneReferenceRun(update: Partial<EvaluationRun> = {}): EvaluationRun {
  return {
    ...structuredClone(referenceRun),
    ...update,
  };
}

describe("evaluation reference data", () => {
  it("contains the validated benchmark with four engines and 22 metrics", () => {
    expect(referenceRun.run_id).toBe("a5f04b52deda4ba6a0a356d5bf48deb6");
    expect(Object.keys(referenceRun.measured_metrics)).toEqual(expectedEngines);
    expect(Object.keys(referenceRun.ir_metrics)).toEqual(expectedEngines);
    expect(dashboardMetrics).toHaveLength(22);
    for (const engine of expectedEngines) {
      expect(referenceRun.ir_metrics[engine].judgment_source).toBe("qwen");
    }
  });

  it("keeps the reference for identical, empty, and invalid API responses", () => {
    expect(synchronizeEvaluationRuns(referenceEvaluationRuns, referenceEvaluationRuns))
      .toEqual({ runs: referenceEvaluationRuns, source: "reference" });
    expect(synchronizeEvaluationRuns(referenceEvaluationRuns, []))
      .toEqual({ runs: referenceEvaluationRuns, source: "reference" });
    expect(synchronizeEvaluationRuns(referenceEvaluationRuns, [{ run_id: "invalid" }]))
      .toEqual({ runs: referenceEvaluationRuns, source: "reference" });
  });

  it("adopts a complete newer API benchmark for the current session", () => {
    const newer = cloneReferenceRun({
      run_id: "newer-run",
      created_at: "2026-11-05T15:38:15.118685Z",
    });

    expect(synchronizeEvaluationRuns(referenceEvaluationRuns, [newer])).toEqual({
      runs: [newer],
      source: "synchronized",
    });
  });

  it("preserves null values used for unavailable metrics", () => {
    const withUnavailable = cloneReferenceRun();
    withUnavailable.measured_metrics.BM25.source_hit_at_1 = null;
    withUnavailable.ir_metrics.BM25.ndcg_at_3.value = null;

    expect(isEvaluationRunList([withUnavailable])).toBe(true);
    expect(withUnavailable.measured_metrics.BM25.source_hit_at_1).toBeNull();
    expect(withUnavailable.ir_metrics.BM25.ndcg_at_3.value).toBeNull();
  });
});
