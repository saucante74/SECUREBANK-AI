import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, type ApiErrorCategory } from "../api/client";
import { askRag } from "../api/services";
import type { RagAskResponse } from "../api/types";
import { App } from "../app/App";
import i18n, { changeLanguage } from "../i18n";
import { AssistantPage } from "./AssistantPage";

vi.mock("../api/services", () => ({
  askRag: vi.fn(),
}));

const askRagMock = vi.mocked(askRag);
const testToken = "synthetic-test-token";

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

function tokenInput(): HTMLInputElement {
  return screen.getByLabelText(i18n.t("assistant.developmentToken.label"));
}

function questionInput(): HTMLTextAreaElement {
  return screen.getByRole("textbox", {
    name: i18n.t("assistant.questionLabel"),
  });
}

function useDevelopmentToken(token = testToken): void {
  fireEvent.change(tokenInput(), { target: { value: token } });
  fireEvent.click(
    screen.getByRole("button", {
      name: i18n.t("assistant.developmentToken.use"),
    }),
  );
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
    await i18n.changeLanguage("fr");
  });

  it("shows the development panel only in DEV mode", () => {
    const developmentView = render(<AssistantPage isDevelopment />);

    expect(
      screen.getByRole("heading", { name: "Accès JWT de développement" }),
    ).toBeInTheDocument();
    developmentView.unmount();

    render(<AssistantPage isDevelopment={false} />);
    expect(
      screen.queryByRole("heading", { name: "Accès JWT de développement" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Authentification indisponible" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Envoyer" })).toBeDisabled();
  });

  it("uses a masked token field and clears its visible draft", () => {
    render(<AssistantPage isDevelopment />);

    expect(tokenInput()).toHaveAttribute("type", "password");
    fireEvent.change(tokenInput(), { target: { value: testToken } });
    useDevelopmentToken();

    expect(tokenInput()).toHaveValue("");
    expect(screen.getByText("Un jeton de développement est actif en mémoire.")).toBeInTheDocument();
  });

  it("keeps the token in memory only and loses it after remount", () => {
    const view = render(<AssistantPage isDevelopment />);
    useDevelopmentToken();

    expect(JSON.stringify(window.localStorage)).not.toContain(testToken);
    expect(JSON.stringify(window.sessionStorage)).not.toContain(testToken);
    expect(document.cookie).not.toContain(testToken);

    view.unmount();
    render(<AssistantPage isDevelopment />);
    expect(screen.getByText("Aucun jeton de développement actif.")).toBeInTheDocument();
  });

  it("enables submission only with a token and a non-blank valid question", () => {
    render(<AssistantPage isDevelopment />);
    const sendButton = screen.getByRole("button", { name: "Envoyer" });

    enterQuestion();
    expect(sendButton).toBeDisabled();
    useDevelopmentToken();
    fireEvent.change(questionInput(), { target: { value: "   " } });
    expect(sendButton).toBeDisabled();
    enterQuestion();
    expect(sendButton).toBeEnabled();
  });

  it("calls askRag with the question, token, and AbortSignal", async () => {
    askRagMock.mockResolvedValue(responseFixture);
    render(<AssistantPage isDevelopment />);
    useDevelopmentToken();
    enterQuestion();

    sendQuestion();

    await waitFor(() => {
      expect(askRagMock).toHaveBeenCalledTimes(1);
    });
    expect(askRagMock).toHaveBeenCalledWith(
      { question: "Question envoyée" },
      testToken,
      undefined,
      expect.any(AbortSignal),
    );
  });

  it("shows loading, preserves the question, and blocks duplicate submissions", () => {
    const pendingResponse = deferred<RagAskResponse>();
    askRagMock.mockReturnValue(pendingResponse.promise);
    render(<AssistantPage isDevelopment />);
    useDevelopmentToken();
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
    render(<AssistantPage isDevelopment />);
    useDevelopmentToken();
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
    render(<AssistantPage isDevelopment />);
    useDevelopmentToken();
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
    ["HTTP 401", "unauthenticated", 401, "Une authentification est requise."],
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
    render(<AssistantPage isDevelopment />);
    useDevelopmentToken();
    enterQuestion();
    sendQuestion();

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });

  it("does not display an alarming error for a voluntary cancellation", async () => {
    askRagMock.mockImplementation(
      (_request, _token, _client, signal) =>
        new Promise((_resolve, reject) => {
          signal?.addEventListener("abort", () => {
            reject(new ApiError({ category: "aborted", method: "POST" }));
          });
        }),
    );
    render(<AssistantPage isDevelopment />);
    useDevelopmentToken();
    enterQuestion();
    sendQuestion();

    fireEvent.click(screen.getByRole("button", { name: "Effacer" }));

    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "Conversation vide" })).toBeInTheDocument();
  });

  it("aborts the active request on unmount", () => {
    let requestSignal: AbortSignal | undefined;
    askRagMock.mockImplementation((_request, _token, _client, signal) => {
      requestSignal = signal;
      return new Promise(() => undefined);
    });
    const view = render(<AssistantPage isDevelopment />);
    useDevelopmentToken();
    enterQuestion();
    sendQuestion();

    view.unmount();

    expect(requestSignal?.aborted).toBe(true);
  });

  it("aborts the active request when leaving the Assistant page", () => {
    let requestSignal: AbortSignal | undefined;
    askRagMock.mockImplementation((_request, _token, _client, signal) => {
      requestSignal = signal;
      return new Promise(() => undefined);
    });
    window.history.replaceState({}, "", "/assistant");
    render(<App />);
    useDevelopmentToken();
    enterQuestion();
    sendQuestion();
    const navigation = screen.getByRole("navigation", {
      name: "Sections de l’application",
    });

    fireEvent.click(within(navigation).getByRole("link", { name: "Accueil" }));

    expect(requestSignal?.aborted).toBe(true);
  });

  it("aborts and ignores an obsolete response after token clearing", async () => {
    const pendingResponse = deferred<RagAskResponse>();
    let requestSignal: AbortSignal | undefined;
    askRagMock.mockImplementation((_request, _token, _client, signal) => {
      requestSignal = signal;
      return pendingResponse.promise;
    });
    render(<AssistantPage isDevelopment />);
    useDevelopmentToken();
    enterQuestion();
    sendQuestion();

    fireEvent.click(screen.getByRole("button", { name: "Effacer" }));
    expect(requestSignal?.aborted).toBe(true);
    await act(async () => {
      pendingResponse.resolve(responseFixture);
      await pendingResponse.promise;
    });

    expect(
      screen.queryByText("Réponse réelle simulée par le service mocké [1]."),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Conversation vide" })).toBeInTheDocument();
  });

  it("translates request states without translating RAG content", async () => {
    askRagMock.mockResolvedValue(responseFixture);
    await changeLanguage("it");
    render(<AssistantPage isDevelopment />);
    useDevelopmentToken();
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
    render(<AssistantPage isDevelopment />);
    useDevelopmentToken();
    enterQuestion();
    sendQuestion();

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });

  it("does not call askRag automatically or without a token", () => {
    render(<AssistantPage isDevelopment />);
    expect(askRagMock).not.toHaveBeenCalled();
    enterQuestion();
    const form = screen.getByRole("button", { name: "Envoyer" }).closest("form");
    expect(form).not.toBeNull();
    fireEvent.submit(form as HTMLFormElement);
    expect(askRagMock).not.toHaveBeenCalled();
  });
});
