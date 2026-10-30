import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { compareEvaluationRuns, getEvaluationRuns } from "../api/services";
import type { EvaluationRun } from "../api/types";
import { EvaluationPage } from "./EvaluationPage";

vi.mock("../api/services", () => ({
  compareEvaluationRuns: vi.fn(),
  getEvaluationRuns: vi.fn(),
}));

const getRunsMock = vi.mocked(getEvaluationRuns);
const compareRunsMock = vi.mocked(compareEvaluationRuns);

const run: EvaluationRun = {
  benchmark_id: "securebank-rag-retrieval-v1",
  run_id: "run-1",
  created_at: "2026-10-30T12:00:00Z",
  code_version: "a".repeat(40),
  rag_configuration: { top_k: 3 },
  parameter_change: null,
  measured_metrics: {
    BM25: {
      source_hit_at_1: 0.575,
      source_hit_at_3: 0.8,
      evidence_hit_at_1: 0.45,
      evidence_hit_at_3: 0.7,
      mean_latency_seconds: 0.001,
    },
    RRF: {
      source_hit_at_1: 0.6,
      source_hit_at_3: 0.8,
      evidence_hit_at_1: 0.425,
      evidence_hit_at_3: 0.675,
      mean_latency_seconds: 0.015,
    },
  },
  expected_behaviors: [],
  uncomputed_metrics: ["answer_correctness"],
  langfuse_trace_ids: [],
};

describe("EvaluationPage", () => {
  beforeEach(() => {
    getRunsMock.mockReset();
    compareRunsMock.mockReset();
  });

  it("shows the dashboard and one history row per engine", async () => {
    getRunsMock.mockResolvedValue([run]);

    render(<EvaluationPage onSessionExpired={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Évaluation du RAG" })).toBeInTheDocument();
    expect(screen.getAllByText("0.700")).toHaveLength(2);
    const table = screen.getByRole("table");
    expect(within(table).getByText("BM25")).toBeInTheDocument();
    expect(within(table).getByText("RRF")).toBeInTheDocument();
  });

  it("shows the empty state without inventing metrics", async () => {
    getRunsMock.mockResolvedValue([]);

    render(<EvaluationPage onSessionExpired={vi.fn()} />);

    expect(await screen.findByText("Aucun benchmark historique n’est disponible.")).toBeInTheDocument();
    expect(screen.getAllByText("—")).toHaveLength(2);
  });

  it("compares runs through the protected API", async () => {
    const older = { ...run, run_id: "run-0", created_at: "2026-10-29T12:00:00Z" };
    getRunsMock.mockResolvedValue([run, older]);
    compareRunsMock.mockResolvedValue({
      previous_run_id: "run-0",
      new_run_id: "run-1",
      configuration_changes: [
        { name: "top_k", previous_value: 2, new_value: 3 },
      ],
      metric_deltas: [
        {
          engine: "RRF",
          metric: "evidence_hit_at_3",
          previous_value: 0.6,
          new_value: 0.675,
          delta: 0.075,
        },
      ],
    });

    render(<EvaluationPage onSessionExpired={vi.fn()} />);
    await screen.findAllByText("run-0");
    fireEvent.click(screen.getByRole("button", { name: "Comparer" }));

    await waitFor(() => {
      expect(compareRunsMock).toHaveBeenCalledWith("run-0", "run-1");
    });
    expect(screen.getByText("top_k: 2 → 3")).toBeInTheDocument();
    expect(screen.getByText(/RRF · Evidence Hit@3: \+0.075/)).toBeInTheDocument();
  });
});
