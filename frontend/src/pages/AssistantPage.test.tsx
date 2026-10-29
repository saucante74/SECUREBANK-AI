import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AssistantPage } from "./AssistantPage";

describe("AssistantPage", () => {
  it("displays its title and empty conversation state", () => {
    render(<AssistantPage />);

    expect(
      screen.getByRole("heading", { name: "Assistant documentaire" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Conversation vide" }),
    ).toBeInTheDocument();
  });

  it("provides an accessible multiline question field", () => {
    render(<AssistantPage />);

    const textarea = screen.getByRole("textbox", {
      name: "Question documentaire",
    });
    expect(textarea.tagName).toBe("TEXTAREA");
    expect(textarea).toHaveAttribute("placeholder", "Saisissez votre question ici.");
  });

  it("updates the character counter including spaces", () => {
    render(<AssistantPage />);
    const textarea = screen.getByRole("textbox", {
      name: "Question documentaire",
    });

    fireEvent.change(textarea, { target: { value: "Une question " } });

    expect(screen.getByText("13 / 2000 caractères")).toBeInTheDocument();
  });

  it("limits the question to 2000 characters", () => {
    render(<AssistantPage />);

    expect(
      screen.getByRole("textbox", { name: "Question documentaire" }),
    ).toHaveAttribute("maxlength", "2000");
  });

  it("keeps public discovery available before authentication", () => {
    render(<AssistantPage />);

    expect(screen.getByRole("button", { name: "Envoyer" })).toBeDisabled();
    expect(
      screen.getByText(
        "La page reste accessible. Une connexion sera demandée uniquement lors de l’envoi.",
      ),
    ).toBeInTheDocument();
  });

  it("opens authentication on a valid anonymous submission without an HTTP request", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<AssistantPage />);
    fireEvent.change(
      screen.getByRole("textbox", { name: "Question documentaire" }),
      { target: { value: "Question conservée" } },
    );
    const button = screen.getByRole("button", { name: "Envoyer" });
    fireEvent.click(button);

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(
      screen.getByRole("dialog", { name: "Connexion requise" }),
    ).toBeInTheDocument();
    fetchSpy.mockRestore();
  });

  it("displays three keyboard-accessible suggested questions", () => {
    render(<AssistantPage />);

    const suggestions = screen.getAllByRole("button", {
      name: /plafond quotidien|documents sont nécessaires|transaction suspecte/,
    });
    expect(suggestions).toHaveLength(3);
    suggestions[0].focus();
    expect(suggestions[0]).toHaveFocus();
  });

  it("replaces the question after an explicit suggestion click without submitting", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<AssistantPage />);
    const question = screen.getByRole("textbox", {
      name: "Question documentaire",
    });
    fireEvent.change(question, { target: { value: "Brouillon existant" } });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Quel est le plafond quotidien des virements en ligne ?",
      }),
    );

    expect(question).toHaveValue(
      "Quel est le plafond quotidien des virements en ligne ?",
    );
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    fetchSpy.mockRestore();
  });

  it("keeps on-demand authentication after selecting a suggestion", () => {
    render(<AssistantPage />);
    fireEvent.click(
      screen.getByRole("button", {
        name: "Quels documents sont nécessaires pour ouvrir un compte bancaire ?",
      }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Envoyer" }));

    expect(
      screen.getByRole("dialog", { name: "Connexion requise" }),
    ).toBeInTheDocument();
  });
});
