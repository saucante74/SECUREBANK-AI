import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import {
  askRag,
  getCurrentUser,
  loginUser,
  logoutUser,
} from "../api/services";
import type { RagAskResponse } from "../api/types";
import { App } from "../app/App";
import i18n, { changeLanguage } from "../i18n";

vi.mock("../api/services", () => ({
  askRag: vi.fn(),
  getCurrentUser: vi.fn(),
  loginUser: vi.fn(),
  logoutUser: vi.fn(),
}));

const askRagMock = vi.mocked(askRag);
const getCurrentUserMock = vi.mocked(getCurrentUser);
const loginUserMock = vi.mocked(loginUser);
const logoutUserMock = vi.mocked(logoutUser);

const identity = { sub: "synthetic-user-id", role: "analyst" } as const;
const ragResponse: RagAskResponse = {
  question: "Question conservée",
  answer: "Réponse documentée [1].",
  sources: [],
  citations: [],
  abstained: false,
};

function renderAssistant(): void {
  window.history.replaceState({}, "", "/assistant");
  render(<App />);
}

function enterQuestion(value = "Question conservée"): HTMLTextAreaElement {
  const question = screen.getByRole("textbox", {
    name: i18n.t("assistant.questionLabel"),
  });
  fireEvent.change(question, { target: { value } });
  return question as HTMLTextAreaElement;
}

function requestAuthentication(): void {
  fireEvent.click(
    screen.getByRole("button", { name: i18n.t("assistant.send") }),
  );
}

function fillLogin(): void {
  fireEvent.change(
    screen.getByRole("textbox", { name: i18n.t("auth.login.username") }),
    { target: { value: "demo.user" } },
  );
  fireEvent.change(screen.getByLabelText(i18n.t("auth.login.password")), {
    target: { value: "synthetic-password" },
  });
}

describe("on-demand authentication", () => {
  beforeEach(async () => {
    askRagMock.mockReset();
    getCurrentUserMock.mockReset();
    loginUserMock.mockReset();
    logoutUserMock.mockReset();
    getCurrentUserMock.mockRejectedValue(
      new ApiError({ category: "unauthenticated", method: "GET", status: 401 }),
    );
    loginUserMock.mockResolvedValue(identity);
    logoutUserMock.mockResolvedValue(undefined);
    askRagMock.mockResolvedValue(ragResponse);
    await i18n.changeLanguage("fr");
  });

  it("opens only after a RAG submission and closes with cancel", () => {
    renderAssistant();

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    const question = enterQuestion();
    requestAuthentication();

    const dialog = screen.getByRole("dialog", { name: "Connexion requise" });
    expect(dialog).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Identifiant" })).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Annuler" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(question).toHaveValue("Question conservée");
    expect(screen.getByRole("button", { name: "Envoyer" })).toHaveFocus();
  });

  it("closes with Escape and restores focus", () => {
    renderAssistant();
    enterQuestion();
    requestAuthentication();

    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Envoyer" })).toHaveFocus();
  });

  it("keeps keyboard focus inside the popup", () => {
    renderAssistant();
    enterQuestion();
    requestAuthentication();
    const username = screen.getByRole("textbox", { name: "Identifiant" });
    const cancel = screen.getByRole("button", { name: "Annuler" });

    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(cancel).toHaveFocus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(username).toHaveFocus();
  });

  it("logs in, preserves the question, and immediately sends it", async () => {
    renderAssistant();
    const question = enterQuestion();
    requestAuthentication();
    fillLogin();

    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));

    await waitFor(() => {
      expect(loginUserMock).toHaveBeenCalledTimes(1);
    });
    expect(loginUserMock).toHaveBeenCalledWith({
      username: "demo.user",
      password: "synthetic-password",
    });
    await waitFor(() => {
      expect(askRagMock).toHaveBeenCalledTimes(1);
    });
    expect(askRagMock).toHaveBeenCalledWith(
      { question: "Question conservée" },
      undefined,
      undefined,
      expect.any(AbortSignal),
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(question).toHaveValue("Question conservée");
    expect(await screen.findByText("Réponse documentée [1].")).toBeInTheDocument();
  });

  it("keeps the popup open with a generic rejected-login message", async () => {
    loginUserMock.mockRejectedValue(
      new ApiError({ category: "unauthenticated", method: "POST", status: 401 }),
    );
    renderAssistant();
    enterQuestion();
    requestAuthentication();
    fillLogin();

    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Identifiant ou mot de passe incorrect.",
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(askRagMock).not.toHaveBeenCalled();
  });

  it("requests authentication again when the RAG session expires", async () => {
    getCurrentUserMock.mockResolvedValue(identity);
    askRagMock.mockRejectedValue(
      new ApiError({ category: "unauthenticated", method: "POST", status: 401 }),
    );
    renderAssistant();
    await screen.findByText("Connecté · analyst");
    const question = enterQuestion();

    requestAuthentication();

    expect(
      await screen.findByRole("dialog", { name: "Connexion requise" }),
    ).toBeInTheDocument();
    expect(question).toHaveValue("Question conservée");
    expect(screen.queryByText("Connecté · analyst")).not.toBeInTheDocument();
  });

  it("logs out, clears session content, and keeps the page public", async () => {
    getCurrentUserMock.mockResolvedValue(identity);
    renderAssistant();
    await screen.findByText("Connecté · analyst");
    enterQuestion();

    fireEvent.click(screen.getByRole("button", { name: "Se déconnecter" }));

    await waitFor(() => {
      expect(logoutUserMock).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(
        screen.getByRole("textbox", { name: "Question documentaire" }),
      ).toHaveValue("");
    });
    expect(
      screen.getByRole("heading", { name: "Assistant documentaire" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Connecté · analyst")).not.toBeInTheDocument();
  });

  it.each([
    ["en", "Sign-in required", "Username", "Cancel"],
    ["it", "Accesso richiesto", "Identificativo", "Annulla"],
  ] as const)(
    "translates the popup in %s",
    async (language, title, usernameLabel, cancelLabel) => {
      await changeLanguage(language);
      renderAssistant();
      enterQuestion("Unchanged question");
      requestAuthentication();

      expect(screen.getByRole("dialog", { name: title })).toBeInTheDocument();
      expect(screen.getByRole("textbox", { name: usernameLabel })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: cancelLabel })).toBeInTheDocument();
    },
  );
});
