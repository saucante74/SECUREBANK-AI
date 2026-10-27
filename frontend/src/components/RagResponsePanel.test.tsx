import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { RagAskResponse } from "../api/types";
import { RagResponsePanel } from "./RagResponsePanel";

const responseFixture: RagAskResponse = {
  question: "Question synthétique",
  answer: "Réponse documentaire synthétique [1].",
  sources: [
    {
      id: "chunk-1",
      document_id: "document-1",
      content: "Extrait documentaire entièrement synthétique.",
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

describe("RagResponsePanel", () => {
  it("presents a normal response", () => {
    render(<RagResponsePanel response={responseFixture} />);

    expect(screen.getByText("Réponse documentaire")).toBeInTheDocument();
    expect(
      screen.getByText("Réponse documentaire synthétique [1]."),
    ).toBeInTheDocument();
  });

  it("presents sources and links matching citations", () => {
    render(<RagResponsePanel response={responseFixture} />);

    const sources = screen.getByRole("heading", { name: "Sources" }).parentElement;
    expect(sources).not.toBeNull();
    expect(within(sources as HTMLElement).getByText("Document synthétique")).toBeInTheDocument();
    expect(
      within(sources as HTMLElement).getByText(
        "Extrait documentaire entièrement synthétique.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Référence 1" })).toHaveAttribute(
      "href",
      "#rag-source-1",
    );
  });

  it("does not link a citation when identifiers do not match", () => {
    const unmatchedResponse: RagAskResponse = {
      ...responseFixture,
      citations: [
        {
          reference: 2,
          document_id: "document-2",
          chunk_id: "chunk-2",
        },
      ],
    };

    render(<RagResponsePanel response={unmatchedResponse} />);

    expect(screen.queryByRole("link", { name: "Référence 2" })).not.toBeInTheDocument();
    expect(screen.getByText("Source associée non disponible.")).toBeInTheDocument();
  });

  it("presents abstention as a distinct business state", () => {
    const abstentionFixture: RagAskResponse = {
      ...responseFixture,
      answer: "Les éléments synthétiques ne permettent pas de répondre.",
      citations: [],
      abstained: true,
    };

    render(<RagResponsePanel response={abstentionFixture} />);

    expect(screen.getByRole("status")).toHaveTextContent("Réponse avec abstention");
    expect(
      screen.getByText("Les éléments synthétiques ne permettent pas de répondre."),
    ).toBeInTheDocument();
    expect(screen.getByText("Aucune citation disponible.")).toBeInTheDocument();
  });
});
