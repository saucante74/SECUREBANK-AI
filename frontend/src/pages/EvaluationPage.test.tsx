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
      latency_p50_seconds: null,
      latency_p95_seconds: null,
      error_rate: null,
      mean_returned_chunk_count: null,
      mean_distinct_document_count_at_3: null,
      mean_source_diversity_at_3: null,
    },
    Qdrant: {
      source_hit_at_1: 0.55,
      source_hit_at_3: 0.75,
      evidence_hit_at_1: 0.4,
      evidence_hit_at_3: 0.65,
      mean_latency_seconds: 0.012,
      latency_p50_seconds: null,
      latency_p95_seconds: null,
      error_rate: null,
      mean_returned_chunk_count: null,
      mean_distinct_document_count_at_3: null,
      mean_source_diversity_at_3: null,
    },
    RRF: {
      source_hit_at_1: 0.6,
      source_hit_at_3: 0.8,
      evidence_hit_at_1: 0.425,
      evidence_hit_at_3: 0.675,
      mean_latency_seconds: 0.015,
      precision_at_1: 0.72,
      latency_p50_seconds: 0.012,
      latency_p95_seconds: 0.03,
      error_rate: 0.025,
      mean_returned_chunk_count: 2.8,
      mean_distinct_document_count_at_3: 2.1,
      mean_source_diversity_at_3: 0.75,
    },
    "RRF + FlashRank": {
      source_hit_at_1: 0.625,
      source_hit_at_3: 0.825,
      evidence_hit_at_1: 0.475,
      evidence_hit_at_3: 0.725,
      mean_latency_seconds: 0.02,
      latency_p50_seconds: null,
      latency_p95_seconds: null,
      error_rate: null,
      mean_returned_chunk_count: null,
      mean_distinct_document_count_at_3: null,
      mean_source_diversity_at_3: null,
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

    expect(await screen.findByRole("heading", { name: "Évaluation RAG" })).toBeInTheDocument();
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
    expect(screen.queryByText("N/A")).not.toBeInTheDocument();
  });

  it("selects the latest run by date instead of API order and defaults to RRF", async () => {
    const older = {
      ...run,
      run_id: "run-old",
      created_at: "2026-10-29T12:00:00Z",
      measured_metrics: {
        ...run.measured_metrics,
        RRF: { ...run.measured_metrics.RRF, precision_at_1: 0.11 },
      },
    };
    const latest = { ...run, run_id: "run-latest", created_at: "2026-10-31T12:00:00Z" };
    getRunsMock.mockResolvedValue([older, latest]);

    render(<EvaluationPage />);

    const summary = (await screen.findByRole("heading", {
      name: "Dernier benchmark disponible",
    })).closest("section");
    expect(summary).not.toBeNull();
    expect(within(summary as HTMLElement).getByText("run-latest")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Moteur évalué" })).toHaveValue("RRF");
    const precision = screen.getByRole("heading", { name: "Precision@1" }).closest("article");
    expect(within(precision as HTMLElement).getByText("72,0")).toBeInTheDocument();
    expect(within(precision as HTMLElement).getByText("%")).toBeInTheDocument();
    const latency = screen.getByRole("heading", { name: "Latence moyenne" }).closest("article");
    expect(within(latency as HTMLElement).getByText("15,0")).toBeInTheDocument();
    expect(within(latency as HTMLElement).getByText("ms")).toBeInTheDocument();
    const p50 = screen.getByRole("heading", { name: "Latence P50" }).closest("article");
    expect(within(p50 as HTMLElement).getByText("12,0")).toBeInTheDocument();
    const p95 = screen.getByRole("heading", { name: "Latence P95" }).closest("article");
    expect(within(p95 as HTMLElement).getByText("30,0")).toBeInTheDocument();
    const errorRate = screen.getByRole("heading", { name: "Taux d’erreur" }).closest("article");
    expect(within(errorRate as HTMLElement).getByText("2,5")).toBeInTheDocument();
    const chunks = screen.getByRole("heading", { name: "Chunks moyens retournés" }).closest("article");
    expect(within(chunks as HTMLElement).getByText("2,8")).toBeInTheDocument();
    const documents = screen.getByRole("heading", { name: "Documents distincts@3" }).closest("article");
    expect(within(documents as HTMLElement).getByText("2,1")).toBeInTheDocument();
    const diversity = screen.getByRole("heading", { name: "Diversité des sources@3" }).closest("article");
    expect(within(diversity as HTMLElement).getByText("75,0")).toBeInTheDocument();
  });

  it("uses run id as a deterministic tie-breaker", async () => {
    const runA = { ...run, run_id: "run-a" };
    const runZ = { ...run, run_id: "run-z" };
    getRunsMock.mockResolvedValue([runA, runZ]);

    render(<EvaluationPage />);

    const summary = (await screen.findByRole("heading", {
      name: "Dernier benchmark disponible",
    })).closest("section");
    expect(within(summary as HTMLElement).getByText("run-z")).toBeInTheDocument();
  });

  it("changes every dashboard card to the selected engine and keeps missing metrics unavailable", async () => {
    getRunsMock.mockResolvedValue([run]);

    render(<EvaluationPage />);

    const selector = await screen.findByRole("combobox", { name: "Moteur évalué" });
    fireEvent.change(selector, { target: { value: "Qdrant" } });

    const source = screen.getByRole("heading", { name: "Source Hit@1" }).closest("article");
    expect(within(source as HTMLElement).getByText("55,0")).toBeInTheDocument();
    const precision = screen.getByRole("heading", { name: "Precision@1" }).closest("article");
    expect(within(precision as HTMLElement).getByText("N/A")).toBeInTheDocument();
    const p50 = screen.getByRole("heading", { name: "Latence P50" }).closest("article");
    expect(within(p50 as HTMLElement).getByText("N/A")).toBeInTheDocument();
  });

  it("shows loading and API error states", async () => {
    let rejectRequest: (reason: unknown) => void = () => undefined;
    getRunsMock.mockImplementation(
      () => new Promise((_, reject) => {
        rejectRequest = reject;
      }),
    );

    render(<EvaluationPage />);
    expect(screen.getByRole("status")).toHaveTextContent("Chargement des benchmarks…");
    rejectRequest(new Error("unavailable"));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Les benchmarks ne peuvent pas être chargés actuellement.",
    );
  });

  it("provides keyboard-accessible metric guide sections", async () => {
    getRunsMock.mockResolvedValue([run]);

    render(<EvaluationPage />);

    const relevance = await screen.findByText("Pertinence", { selector: "summary" });
    relevance.focus();
    expect(relevance).toHaveFocus();
    fireEvent.click(relevance);
    expect(relevance.parentElement).toHaveAttribute("open");
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
