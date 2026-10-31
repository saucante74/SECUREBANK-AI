import { StrictMode } from "react";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { getCurrentUser, getEvaluationRuns } from "../api/services";
import { App } from "./App";

vi.mock("../api/services", () => ({
  askRag: vi.fn(),
  compareEvaluationRuns: vi.fn(),
  getEvaluationRuns: vi.fn(),
  getCurrentUser: vi.fn(),
  loginUser: vi.fn(),
  logoutUser: vi.fn(),
}));

const getCurrentUserMock = vi.mocked(getCurrentUser);
const getEvaluationRunsMock = vi.mocked(getEvaluationRuns);

function navigation(): HTMLElement {
  return screen.getByRole("navigation", { name: "Sections de l’application" });
}

describe("App navigation", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    getCurrentUserMock.mockReset();
    getEvaluationRunsMock.mockReset();
    getEvaluationRunsMock.mockResolvedValue([]);
    getCurrentUserMock.mockRejectedValue(
      new ApiError({ category: "unauthenticated", method: "GET", status: 401 }),
    );
  });

  it("keeps the home page accessible", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", {
        name: "Assistant bancaire intelligent et sécurisé",
      }),
    ).toBeInTheDocument();
    expect(within(navigation()).getByRole("link", { name: "Accueil" })).toHaveAttribute(
      "href",
      "/",
    );
  });

  it("hides evaluation from anonymous users and protects direct access", async () => {
    window.history.replaceState({}, "", "/evaluation");
    render(<App />);

    await waitFor(() => {
      expect(window.location.pathname).toBe("/");
    });
    expect(within(navigation()).queryByRole("link", { name: "Évaluation" })).not.toBeInTheDocument();
  });

  it("shows evaluation navigation to administrators", async () => {
    getCurrentUserMock.mockResolvedValue({ sub: "admin", role: "admin" });
    window.history.replaceState({}, "", "/evaluation");
    render(<App />);

    expect(await within(navigation()).findByRole("link", { name: "Évaluation" })).toBeInTheDocument();
  });

  it("keeps the restored administrator session under StrictMode", async () => {
    let rejectDiscardedRequest: (reason: unknown) => void = () => undefined;
    getCurrentUserMock
      .mockImplementationOnce(
        () =>
          new Promise((_, reject) => {
            rejectDiscardedRequest = reject;
          }),
      )
      .mockResolvedValueOnce({ sub: "admin", role: "admin" });

    render(
      <StrictMode>
        <App />
      </StrictMode>,
    );

    expect(
      await within(navigation()).findByRole("link", { name: "Évaluation" }),
    ).toBeInTheDocument();

    await act(async () => {
      rejectDiscardedRequest(
        new ApiError({ category: "aborted", method: "GET" }),
      );
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(
        within(navigation()).getByRole("link", { name: "Évaluation" }),
      ).toBeInTheDocument();
    });
  });

  it("navigates to the assistant and back home", () => {
    render(<App />);

    fireEvent.click(within(navigation()).getByRole("link", { name: "Assistant" }));
    expect(
      screen.getByRole("heading", { name: "Assistant documentaire" }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe("/assistant");

    fireEvent.click(within(navigation()).getByRole("link", { name: "Accueil" }));
    expect(
      screen.getByRole("heading", {
        name: "Assistant bancaire intelligent et sécurisé",
      }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe("/");
  });

  it("supports browser previous and next navigation", async () => {
    render(<App />);
    fireEvent.click(within(navigation()).getByRole("link", { name: "Assistant" }));

    act(() => {
      window.history.back();
    });
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Assistant bancaire intelligent et sécurisé",
        }),
      ).toBeInTheDocument(),
    );

    act(() => {
      window.history.forward();
    });
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Assistant documentaire" }),
      ).toBeInTheDocument(),
    );
  });

  it("supports direct access to the assistant", () => {
    window.history.replaceState({}, "", "/assistant");

    render(<App />);

    expect(
      screen.getByRole("heading", { name: "Assistant documentaire" }),
    ).toBeInTheDocument();
  });

  it("preserves the assistant page after a remount", () => {
    window.history.replaceState({}, "", "/assistant");
    const view = render(<App />);

    view.unmount();
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "Assistant documentaire" }),
    ).toBeInTheDocument();
  });

  it("marks only the active page with aria-current", () => {
    render(<App />);
    fireEvent.click(within(navigation()).getByRole("link", { name: "Assistant" }));

    expect(
      within(navigation()).getByRole("link", { name: "Assistant" }),
    ).toHaveAttribute("aria-current", "page");
    expect(
      within(navigation()).getByRole("link", { name: "Accueil" }),
    ).not.toHaveAttribute("aria-current");
  });

  it("navigates to the public About page", () => {
    render(<App />);

    fireEvent.click(within(navigation()).getByRole("link", { name: "À propos" }));

    expect(
      screen.getByRole("heading", { name: "À propos de SecureBank-AI" }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe("/about");
    expect(
      within(navigation()).getByRole("link", { name: "À propos" }),
    ).toHaveAttribute("aria-current", "page");
  });

  it("places the compact language control immediately before sign-in", async () => {
    render(<App />);

    const languageControl = screen.getByRole("group", {
      name: "Langue de l’interface",
    });
    const loginButton = await screen.findByRole("button", {
      name: "Se connecter",
    });

    expect(languageControl.nextElementSibling).toBe(loginButton);
    expect(within(languageControl).getAllByRole("button")).toHaveLength(4);
  });

  it("closes the mobile menu after navigation", () => {
    render(<App />);
    const menuButton = screen.getByRole("button", {
      name: "Ouvrir la navigation",
    });

    fireEvent.click(menuButton);
    fireEvent.click(within(navigation()).getByRole("link", { name: "Assistant" }));

    expect(menuButton).toHaveAttribute("aria-expanded", "false");
    expect(menuButton).toHaveFocus();
  });

  it("checks the optional session without blocking public navigation", async () => {
    render(<App />);
    fireEvent.click(within(navigation()).getByRole("link", { name: "Assistant" }));

    await waitFor(() => {
      expect(getCurrentUserMock).toHaveBeenCalledTimes(1);
    });
    expect(
      screen.getByRole("heading", { name: "Assistant documentaire" }),
    ).toBeInTheDocument();
  });
});
