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
  run_id: "run-1",
  created_at: "2026-10-30T12:00:00Z",
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
    Qdrant: {
      source_hit_at_1: 0.55,
      source_hit_at_3: 0.75,
      evidence_hit_at_1: 0.4,
      evidence_hit_at_3: 0.65,
      mean_latency_seconds: 0.012,
    },
    RRF: {
      source_hit_at_1: 0.6,
      source_hit_at_3: 0.8,
      evidence_hit_at_1: 0.425,
      evidence_hit_at_3: 0.675,
      mean_latency_seconds: 0.015,
    },
    "RRF + FlashRank": {
      source_hit_at_1: 0.625,
      source_hit_at_3: 0.825,
      evidence_hit_at_1: 0.475,
      evidence_hit_at_3: 0.725,
      mean_latency_seconds: 0.02,
    },
  },
};

describe("EvaluationPage", () => {
  beforeEach(() => {
    getRunsMock.mockReset();
    compareRunsMock.mockReset();
  });

  it("groups four engines under one collapsed run row", async () => {
    getRunsMock.mockResolvedValue([run]);

    render(<EvaluationPage />);

    expect(await screen.findByRole("heading", { name: "Évaluation du RAG" })).toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(2);
    expect(within(table).queryByText("BM25")).not.toBeInTheDocument();
    expect(within(table).queryByText("Qdrant")).not.toBeInTheDocument();
    expect(within(table).queryByText("RRF")).not.toBeInTheDocument();
    expect(within(table).queryByText("RRF + FlashRank")).not.toBeInTheDocument();
    expect(within(table).getByText("run-1")).toBeInTheDocument();
    expect(within(table).getByText("4")).toBeInTheDocument();
  });

  it("expands the four engine rows with their metrics and collapses them again", async () => {
    getRunsMock.mockResolvedValue([run]);

    render(<EvaluationPage />);

    const expandButton = await screen.findByRole("button", {
      name: "Développer les moteurs du run run-1",
    });
    expect(expandButton).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(expandButton);

    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(6);
    const bm25Row = within(table).getByRole("row", { name: /BM25/ });
    expect(within(bm25Row).getByText("0.575")).toBeInTheDocument();
    expect(within(bm25Row).getByText("0.800")).toBeInTheDocument();
    expect(within(bm25Row).getByText("0.450")).toBeInTheDocument();
    expect(within(bm25Row).getByText("0.700")).toBeInTheDocument();
    expect(within(bm25Row).getByText("1.0 ms")).toBeInTheDocument();
    expect(within(table).getByText("Qdrant")).toBeInTheDocument();
    expect(within(table).getByText("RRF")).toBeInTheDocument();
    expect(within(table).getByText("RRF + FlashRank")).toBeInTheDocument();

    const collapseButton = screen.getByRole("button", {
      name: "Réduire les moteurs du run run-1",
    });
    expect(collapseButton).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(collapseButton);
    expect(within(table).getAllByRole("row")).toHaveLength(2);
    expect(within(table).queryByText("BM25")).not.toBeInTheDocument();
  });

  it("uses a keyboard-focusable disclosure control with an ARIA relationship", async () => {
    getRunsMock.mockResolvedValue([run]);

    render(<EvaluationPage />);

    const button = await screen.findByRole("button", {
      name: "Développer les moteurs du run run-1",
    });
    button.focus();

    expect(button).toHaveFocus();
    expect(button).toHaveAttribute("aria-controls", "evaluation-run-run-1-engines");
    expect(document.getElementById("evaluation-run-run-1-engines")).toBeInTheDocument();
  });

  it("shows the empty state without inventing metrics", async () => {
    getRunsMock.mockResolvedValue([]);

    render(<EvaluationPage />);

    expect(await screen.findByText("Aucun benchmark historique n’est disponible.")).toBeInTheDocument();
    expect(screen.getAllByText("—")).toHaveLength(2);
  });

  it("compares runs through the public API", async () => {
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

    render(<EvaluationPage />);
    await screen.findAllByText("run-0");
    fireEvent.click(screen.getByRole("button", { name: "Comparer" }));

    await waitFor(() => {
      expect(compareRunsMock).toHaveBeenCalledWith("run-0", "run-1");
    });
    expect(screen.getByText("top_k: 2 → 3")).toBeInTheDocument();
    expect(screen.getByText(/RRF · Evidence Hit@3: \+0.075/)).toBeInTheDocument();
  });
});
