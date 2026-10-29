import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, type ApiErrorCategory } from "../api/client";
import { askRag, getCurrentUser } from "../api/services";
import type { RagAskResponse } from "../api/types";
import { App } from "../app/App";
import i18n, { changeLanguage } from "../i18n";
import { AssistantPage } from "./AssistantPage";

vi.mock("../api/services", () => ({
  askRag: vi.fn(),
  getCurrentUser: vi.fn(),
  loginUser: vi.fn(),
  logoutUser: vi.fn(),
}));

const askRagMock = vi.mocked(askRag);
const getCurrentUserMock = vi.mocked(getCurrentUser);
const authenticatedUser = {
  sub: "synthetic-user-id",
  role: "compliance_officer",
} as const;

const responseFixture: RagAskResponse = {
  question: "Question envoyée",
  answer: "Réponse réelle simulée par le service mocké [1].",
  sources: [
    {
      id: "chunk-1",
      document_id: "document-1",
      content: "Extrait synthétique retourné par le service mocké.",
      position: 0,
      title: "Document synthétique retourné",
      source: "synthetic://document-1",
    },
  ],
  citations: [
    {
      reference: 1,
      document_id: "document-1",
      chunk_id: "chunk-1",
    },
  ],
  abstained: false,
};

interface Deferred<Value> {
  promise: Promise<Value>;
  reject: (reason?: unknown) => void;
  resolve: (value: Value) => void;
}

function deferred<Value>(): Deferred<Value> {
  let resolvePromise: (value: Value) => void = () => undefined;
  let rejectPromise: (reason?: unknown) => void = () => undefined;
  const promise = new Promise<Value>((resolve, reject) => {
    resolvePromise = resolve;
    rejectPromise = reject;
  });
  return { promise, reject: rejectPromise, resolve: resolvePromise };
}

function questionInput(): HTMLTextAreaElement {
  return screen.getByRole("textbox", {
    name: i18n.t("assistant.questionLabel"),
  });
}

function enterQuestion(question = "Question envoyée"): void {
  fireEvent.change(questionInput(), { target: { value: question } });
}

function sendQuestion(): void {
  fireEvent.click(
    screen.getByRole("button", { name: i18n.t("assistant.send") }),
  );
}

describe("Assistant RAG integration", () => {
  beforeEach(async () => {
    askRagMock.mockReset();
    getCurrentUserMock.mockReset();
    getCurrentUserMock.mockRejectedValue(
      new ApiError({ category: "unauthenticated", method: "GET", status: 401 }),
    );
    await i18n.changeLanguage("fr");
  });

  it("enables on-demand authentication for a non-blank valid question", () => {
    render(<AssistantPage authStatus="authenticated" />);
    const sendButton = screen.getByRole("button", { name: "Envoyer" });

    enterQuestion();
    expect(sendButton).toBeEnabled();
    fireEvent.change(questionInput(), { target: { value: "   " } });
    expect(sendButton).toBeDisabled();
    enterQuestion();
    expect(sendButton).toBeEnabled();
  });

  it("calls askRag with the question, cookie session, and AbortSignal", async () => {
    askRagMock.mockResolvedValue(responseFixture);
    render(<AssistantPage authStatus="authenticated" />);
    enterQuestion();

    sendQuestion();

    await waitFor(() => {
      expect(askRagMock).toHaveBeenCalledTimes(1);
    });
    expect(askRagMock).toHaveBeenCalledWith(
      { question: "Question envoyée" },
      undefined,
      undefined,
      expect.any(AbortSignal),
    );
  });

  it("shows loading, preserves the question, and blocks duplicate submissions", () => {
    const pendingResponse = deferred<RagAskResponse>();
    askRagMock.mockReturnValue(pendingResponse.promise);
    render(<AssistantPage authStatus="authenticated" />);
    enterQuestion();

    sendQuestion();

    expect(screen.getByRole("status")).toHaveTextContent(
      "Recherche d’une réponse documentée…",
    );
    expect(questionInput()).toHaveValue("Question envoyée");
    expect(screen.getByRole("button", { name: "Envoyer" })).toBeDisabled();
    sendQuestion();
    expect(askRagMock).toHaveBeenCalledTimes(1);
  });

  it("displays the returned answer, sources, and citations", async () => {
    askRagMock.mockResolvedValue(responseFixture);
    render(<AssistantPage authStatus="authenticated" />);
    enterQuestion();
    sendQuestion();

    expect(
      await screen.findByText("Réponse réelle simulée par le service mocké [1]."),
    ).toBeInTheDocument();
    expect(screen.getByText("Document synthétique retourné")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Référence 1" })).toHaveAttribute(
      "href",
      "#rag-source-1",
    );
  });

  it("displays an abstention as a valid response", async () => {
    askRagMock.mockResolvedValue({
      ...responseFixture,
      answer: "Les éléments fournis ne permettent pas de répondre.",
      citations: [],
      abstained: true,
    });
    render(<AssistantPage authStatus="authenticated" />);
    enterQuestion();
    sendQuestion();

    expect(
      await screen.findByText("Les éléments fournis ne permettent pas de répondre."),
    ).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Réponse avec abstention",
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it.each<[string, ApiErrorCategory, number | undefined, string]>([
    ["HTTP 403", "forbidden", 403, "Vous n’avez pas l’autorisation d’effectuer cette action."],
    ["HTTP 422", "validation", 422, "Les informations envoyées ne sont pas valides."],
    ["HTTP 502", "upstream_service", 502, "Le service de génération ne peut pas répondre actuellement."],
    ["HTTP 503", "service_unavailable", 503, "Le service est temporairement indisponible."],
    ["network", "network", undefined, "La connexion au service a échoué."],
    ["non-JSON response", "unexpected_response", 200, "Le service a renvoyé une réponse inattendue."],
    ["empty response", "unexpected_response", 200, "Le service a renvoyé une réponse inattendue."],
  ])("displays the translated %s error", async (_label, category, status, message) => {
    askRagMock.mockRejectedValue(
      new ApiError({ category, method: "POST", status }),
    );
    render(<AssistantPage authStatus="authenticated" />);
    enterQuestion();
    sendQuestion();

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });

  it("aborts the active request on unmount", () => {
    let requestSignal: AbortSignal | undefined;
    askRagMock.mockImplementation((_request, _token, _client, signal) => {
      requestSignal = signal;
      return new Promise(() => undefined);
    });
    const view = render(<AssistantPage authStatus="authenticated" />);
    enterQuestion();
    sendQuestion();

    view.unmount();

    expect(requestSignal?.aborted).toBe(true);
  });

  it("aborts the active request when leaving the Assistant page", async () => {
    let requestSignal: AbortSignal | undefined;
    askRagMock.mockImplementation((_request, _token, _client, signal) => {
      requestSignal = signal;
      return new Promise(() => undefined);
    });
    window.history.replaceState({}, "", "/assistant");
    getCurrentUserMock.mockResolvedValue(authenticatedUser);
    render(<App />);
    await screen.findByText("Connecté · compliance_officer");
    enterQuestion();
    sendQuestion();
    const navigation = screen.getByRole("navigation", {
      name: "Sections de l’application",
    });

    fireEvent.click(within(navigation).getByRole("link", { name: "Accueil" }));

    expect(requestSignal?.aborted).toBe(true);
  });

  it("translates request states without translating RAG content", async () => {
    askRagMock.mockResolvedValue(responseFixture);
    await changeLanguage("it");
    render(<AssistantPage authStatus="authenticated" />);
    enterQuestion("Domanda invariata");
    sendQuestion();

    expect(
      await screen.findByText("Réponse réelle simulée par le service mocké [1]."),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Risposta" })).toBeInTheDocument();
    expect(questionInput()).toHaveValue("Domanda invariata");
  });

  it.each([
    ["fr", "La connexion au service a échoué."],
    ["en", "The connection to the service failed."],
    ["it", "La connessione al servizio non è riuscita."],
  ] as const)("translates errors in %s", async (language, message) => {
    askRagMock.mockRejectedValue(
      new ApiError({ category: "network", method: "POST" }),
    );
    await changeLanguage(language);
    render(<AssistantPage authStatus="authenticated" />);
    enterQuestion();
    sendQuestion();

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });

  it("does not call askRag automatically or for an anonymous session", () => {
    render(<AssistantPage />);
    expect(askRagMock).not.toHaveBeenCalled();
    enterQuestion();
    const form = screen.getByRole("button", { name: "Envoyer" }).closest("form");
    expect(form).not.toBeNull();
    fireEvent.submit(form as HTMLFormElement);
    expect(askRagMock).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog", { name: "Connexion requise" })).toBeInTheDocument();
  });
});
