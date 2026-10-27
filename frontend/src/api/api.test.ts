import { render } from "@testing-library/react";
import { createElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { App } from "../app/App";
import {
  ApiError,
  createApiClient,
  type ApiErrorCategory,
  type FetchImplementation,
} from "./client";
import { askRag, getCurrentUser, getHealth } from "./services";
import type { RagAskResponse } from "./types";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function createFetch(response: Response): FetchImplementation {
  return vi.fn<FetchImplementation>().mockResolvedValue(response);
}

function requestFrom(fetchMock: FetchImplementation): RequestInit {
  const call = vi.mocked(fetchMock).mock.calls.at(0);
  if (call === undefined) throw new Error("Expected fetch to be called");
  return call[1] ?? {};
}

describe("API services", () => {
  it("calls GET /api/health", async () => {
    const payload = {
      status: "healthy",
      service: "securebank-ai",
      version: "0.1.0",
    };
    const fetchMock = createFetch(jsonResponse(payload));

    await expect(getHealth(createApiClient(fetchMock))).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/health",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("calls GET /api/auth/me with a Bearer token", async () => {
    const payload = { sub: "synthetic-user", role: "analyst" } as const;
    const fetchMock = createFetch(jsonResponse(payload));

    await expect(
      getCurrentUser("synthetic-token", createApiClient(fetchMock)),
    ).resolves.toEqual(payload);

    const headers = new Headers(requestFrom(fetchMock).headers);
    expect(headers.get("Authorization")).toBe("Bearer synthetic-token");
  });

  it("calls POST /api/rag/ask with JSON", async () => {
    const payload: RagAskResponse = {
      question: "Question synthétique",
      answer: "Réponse synthétique [1].",
      sources: [],
      citations: [],
      abstained: true,
    };
    const fetchMock = createFetch(jsonResponse(payload));

    await askRag(
      { question: "Question synthétique", top_k: 2 },
      "synthetic-token",
      createApiClient(fetchMock),
    );

    const options = requestFrom(fetchMock);
    const headers = new Headers(options.headers);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/rag/ask",
      expect.objectContaining({ method: "POST" }),
    );
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(options.body).toBe(
      JSON.stringify({ question: "Question synthétique", top_k: 2 }),
    );
  });

  it("omits Authorization when no token is provided", async () => {
    const fetchMock = createFetch(jsonResponse({ status: "healthy" }));

    await getHealth(createApiClient(fetchMock));

    const headers = new Headers(requestFrom(fetchMock).headers);
    expect(headers.has("Authorization")).toBe(false);
  });

  it.each<[number, ApiErrorCategory, string]>([
    [401, "unauthenticated", "Une authentification est requise."],
    [403, "forbidden", "Vous n’avez pas l’autorisation d’effectuer cette action."],
    [422, "validation", "Les informations envoyées ne sont pas valides."],
    [502, "upstream_service", "Le service de génération ne peut pas répondre actuellement."],
    [503, "service_unavailable", "Le service est temporairement indisponible."],
  ])(
    "maps HTTP %i to a structured error",
    async (status, category, message) => {
      const fetchMock = createFetch(
        jsonResponse({ detail: "Arbitrary server detail" }, status),
      );

      const error = await getHealth(createApiClient(fetchMock)).catch(
        (caught: unknown) => caught,
      );

      expect(error).toBeInstanceOf(ApiError);
      expect(error).toMatchObject({ category, status, method: "GET", message });
      expect((error as ApiError).message).not.toContain("Arbitrary server detail");
    },
  );

  it("maps a network failure", async () => {
    const fetchMock = vi
      .fn<FetchImplementation>()
      .mockRejectedValue(new TypeError("network details"));

    const error = await getHealth(createApiClient(fetchMock)).catch(
      (caught: unknown) => caught,
    );

    expect(error).toMatchObject({
      category: "network",
      method: "GET",
      message: "La connexion au service a échoué.",
    });
  });

  it("rejects an unexpected non-JSON response", async () => {
    const fetchMock = createFetch(new Response("not JSON", { status: 200 }));

    await expect(getHealth(createApiClient(fetchMock))).rejects.toMatchObject({
      category: "unexpected_response",
      status: 200,
    });
  });

  it("rejects an unexpected empty response", async () => {
    const fetchMock = createFetch(new Response(null, { status: 200 }));

    await expect(getHealth(createApiClient(fetchMock))).rejects.toMatchObject({
      category: "unexpected_response",
      status: 200,
    });
  });

  it("maps an aborted request and forwards its signal", async () => {
    const controller = new AbortController();
    const fetchMock = vi
      .fn<FetchImplementation>()
      .mockRejectedValue(new DOMException("aborted", "AbortError"));

    await expect(
      getHealth(createApiClient(fetchMock), controller.signal),
    ).rejects.toMatchObject({ category: "aborted", method: "GET" });
    expect(requestFrom(fetchMock).signal).toBe(controller.signal);
  });

  it("preserves the complete typed RAG response", async () => {
    const payload: RagAskResponse = {
      question: "Question après masquage local",
      answer: "Réponse fondée sur les éléments retournés [1].",
      sources: [
        {
          id: "chunk-1",
          document_id: "document-1",
          content: "Passage synthétique après masquage local.",
          position: 0,
          title: "Document synthétique",
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
    const fetchMock = createFetch(jsonResponse(payload));

    const response = await askRag(
      { question: "Question synthétique" },
      "synthetic-token",
      createApiClient(fetchMock),
    );

    expect(response).toEqual(payload);
    expect(response.sources[0]?.position).toBe(0);
    expect(response.citations[0]?.reference).toBe(1);
  });

  it("does not call the API when App is rendered", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(createElement(App));

    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });
});
