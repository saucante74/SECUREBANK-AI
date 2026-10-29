import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { RagAskResponse } from "../api/types";
import { App } from "../app/App";
import { RagResponsePanel } from "../components/RagResponsePanel";
import i18n, {
  changeLanguage,
  languageStorageKey,
  readLanguagePreference,
} from ".";
import { apiErrorTranslationKey } from "./apiErrorKeys";
import en from "./locales/en.json";
import fr from "./locales/fr.json";
import italianCatalog from "./locales/it.json";

const ragFixture: RagAskResponse = {
  question: "Domanda utente invariata",
  answer: "Réponse générée inchangée [1].",
  sources: [
    {
      id: "chunk-1",
      document_id: "document-1",
      content: "Contenuto documentale invariato.",
      position: 0,
      title: "Titolo documento invariato",
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

function flattenKeys(value: object, prefix = ""): string[] {
  return Object.entries(value).flatMap(([key, entry]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof entry === "object" && entry !== null
      ? flattenKeys(entry as object, path)
      : [path];
  });
}

function languageButton(name: "English" | "Français" | "Italiano"): HTMLButtonElement {
  return screen.getByRole("button", { name });
}

describe("internationalization", () => {
  beforeEach(async () => {
    window.localStorage.clear();
    window.history.replaceState({}, "", "/");
    await i18n.changeLanguage("fr");
  });

  it("uses French by default", () => {
    render(<App />);

    expect(document.documentElement.lang).toBe("fr");
    expect(languageButton("Français")).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.getByRole("heading", {
        name: "Assistant bancaire intelligent et sécurisé",
      }),
    ).toBeInTheDocument();
  });

  it("selects English without reloading or changing the URL", () => {
    render(<App />);
    const pathname = window.location.pathname;

    fireEvent.click(languageButton("English"));

    expect(screen.getByRole("heading", { name: "Secure intelligent banking assistant" })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("en");
    expect(window.location.pathname).toBe(pathname);
  });

  it("selects Italian", () => {
    render(<App />);

    fireEvent.click(languageButton("Italiano"));

    expect(
      screen.getByRole("heading", {
        name: "Assistente bancario intelligente e sicuro",
      }),
    ).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("it");
  });

  it("preserves the current page and user input", () => {
    window.history.replaceState({}, "", "/assistant");
    render(<App />);
    const textarea = screen.getByRole("textbox", {
      name: "Question documentaire",
    });
    fireEvent.change(textarea, { target: { value: "Question conservée" } });

    fireEvent.click(languageButton("English"));

    expect(window.location.pathname).toBe("/assistant");
    expect(screen.getByRole("heading", { name: "Documentary assistant" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Documentary question" })).toHaveValue(
      "Question conservée",
    );
  });

  it("persists only the selected language", () => {
    render(<App />);

    fireEvent.click(languageButton("Italiano"));

    expect(window.localStorage).toHaveLength(1);
    expect(window.localStorage.getItem(languageStorageKey)).toBe("it");
  });

  it("falls back to French for an invalid preference", () => {
    const storage = {
      getItem: vi.fn(() => "de"),
      setItem: vi.fn(),
    };

    expect(readLanguagePreference(storage)).toBe("fr");
  });

  it("remains usable when localStorage is unavailable", async () => {
    const unavailableStorage = {
      getItem: vi.fn(() => {
        throw new DOMException("unavailable", "SecurityError");
      }),
      setItem: vi.fn(() => {
        throw new DOMException("unavailable", "SecurityError");
      }),
    };
    const setItemSpy = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(unavailableStorage.setItem);

    expect(readLanguagePreference(unavailableStorage)).toBe("fr");
    await expect(changeLanguage("en")).resolves.toBeUndefined();
    expect(document.documentElement.lang).toBe("en");
    setItemSpy.mockRestore();
  });

  it("provides a keyboard-accessible segmented language selector", () => {
    render(<App />);
    const englishButton = languageButton("English");

    englishButton.focus();
    fireEvent.keyDown(englishButton, { key: "Enter" });
    fireEvent.click(englishButton);

    expect(englishButton).toHaveFocus();
    expect(englishButton).toHaveAttribute("aria-pressed", "true");
  });

  it("translates navigation and the Assistant page", () => {
    render(<App />);
    fireEvent.click(languageButton("Italiano"));
    const navigation = screen.getByRole("navigation", {
      name: "Sezioni dell’applicazione",
    });

    fireEvent.click(within(navigation).getByRole("link", { name: "Assistente" }));

    expect(screen.getByRole("heading", { name: "Assistente documentale" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Invia" })).toBeDisabled();
  });

  it("translates abstention, source, citation, and error labels", async () => {
    await changeLanguage("en");
    render(<RagResponsePanel response={{ ...ragFixture, abstained: true }} />);

    expect(screen.getByRole("status")).toHaveTextContent("Answer with abstention");
    expect(screen.getByRole("heading", { name: "Sources" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Citations" })).toBeInTheDocument();
    expect(i18n.t(apiErrorTranslationKey("network"))).toBe(
      "The connection to the service failed.",
    );
  });

  it("does not translate RAG content automatically", async () => {
    await changeLanguage("en");
    render(<RagResponsePanel response={ragFixture} />);

    expect(screen.getByText("Réponse générée inchangée [1].")).toBeInTheDocument();
    expect(screen.getByText("Contenuto documentale invariato.")).toBeInTheDocument();
    expect(screen.getByText("Titolo documento invariato")).toBeInTheDocument();
    expect(screen.getByText("synthetic://document-1")).toBeInTheDocument();
    expect(screen.getByText("Document: document-1")).toBeInTheDocument();
  });

  it("loads translations locally without a network request", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<App />);

    fireEvent.click(languageButton("English"));
    fireEvent.click(languageButton("Italiano"));

    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it("keeps identical translation keys in all catalogs", () => {
    const frenchKeys = flattenKeys(fr).sort();

    expect(flattenKeys(en).sort()).toEqual(frenchKeys);
    expect(flattenKeys(italianCatalog).sort()).toEqual(frenchKeys);
  });
});
