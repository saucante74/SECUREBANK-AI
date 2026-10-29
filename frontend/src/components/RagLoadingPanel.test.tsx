import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RagLoadingPanel } from "./RagLoadingPanel";

describe("RagLoadingPanel", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("advances through waiting indications and remains on the final step", () => {
    vi.useFakeTimers();
    render(<RagLoadingPanel />);

    expect(screen.getByText("Analyse de votre question…")).toHaveClass(
      "font-semibold",
    );
    act(() => {
      vi.advanceTimersByTime(1_400);
    });
    expect(screen.getByText("Recherche dans les documents…")).toHaveClass(
      "font-semibold",
    );
    act(() => {
      vi.advanceTimersByTime(2_800);
    });
    expect(screen.getByText("Préparation de la réponse…")).toHaveClass(
      "font-semibold",
    );
    expect(vi.getTimerCount()).toBe(0);
  });

  it("clears its timer when unmounted", () => {
    vi.useFakeTimers();
    const view = render(<RagLoadingPanel />);

    expect(vi.getTimerCount()).toBe(1);
    view.unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
});
