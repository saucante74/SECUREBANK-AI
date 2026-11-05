import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getEvaluationRuns } from "../api/services";
import type { EvaluationRun } from "../api/types";
import { EvaluationPage } from "./EvaluationPage";
import { referenceEvaluationRuns } from "./evaluationData";

vi.mock("../api/services", () => ({
  compareEvaluationRuns: vi.fn(),
  getEvaluationRuns: vi.fn(),
}));

const getRunsMock = vi.mocked(getEvaluationRuns);
const referenceRun = referenceEvaluationRuns[0];

describe("EvaluationPage snapshot synchronization", () => {
  beforeEach(() => {
    getRunsMock.mockReset();
  });

  it("renders the snapshot immediately and keeps it when the API fails", async () => {
    getRunsMock.mockRejectedValue(new Error("unavailable"));

    render(<EvaluationPage />);

    expect(screen.getAllByText(referenceRun.run_id).length).toBeGreaterThan(0);
    expect(screen.getByText(/Données de référence/)).toBeInTheDocument();
    await waitFor(() => {
      expect(getRunsMock).toHaveBeenCalledTimes(1);
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows synchronized provenance for a complete newer benchmark", async () => {
    const newer: EvaluationRun = {
      ...structuredClone(referenceRun),
      run_id: "newer-run",
      created_at: "2026-11-05T15:38:15.118685Z",
    };
    getRunsMock.mockResolvedValue([newer]);

    render(<EvaluationPage />);

    expect(screen.getAllByText(referenceRun.run_id).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("newer-run")).length).toBeGreaterThan(0);
    expect(screen.getByText(/Données synchronisées/)).toBeInTheDocument();
  });
});
