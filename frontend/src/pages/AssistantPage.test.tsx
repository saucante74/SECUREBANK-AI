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

  it("keeps the send button explicitly disabled", () => {
    render(<AssistantPage />);

    expect(screen.getByRole("button", { name: "Envoyer" })).toBeDisabled();
    expect(
      screen.getByText(
        "Ajoutez un JWT de développement pour activer l’envoi.",
      ),
    ).toBeInTheDocument();
  });

  it("prevents form submission without an HTTP request", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<AssistantPage />);
    const button = screen.getByRole("button", { name: "Envoyer" });
    const form = button.closest("form");

    expect(form).not.toBeNull();
    fireEvent.submit(form as HTMLFormElement);

    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });
});
