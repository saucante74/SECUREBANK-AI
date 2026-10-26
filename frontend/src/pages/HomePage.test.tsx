import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "../app/App";

describe("HomePage", () => {
  it("displays the presentation dashboard", () => {
    render(<App />);

    expect(screen.getByText("SecureBank-AI")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Assistant bancaire intelligent et sécurisé",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Confidentialité" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Réponses sourcées" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Fonctionnalités à venir" }),
    ).toBeInTheDocument();
  });

  it("identifies the current and future navigation entries", () => {
    render(<App />);

    const navigation = screen.getByRole("navigation", {
      name: "Sections de l’application",
    });
    const homeEntry = within(navigation).getByText("Accueil").closest("div");
    const assistantEntry = within(navigation).getByText("Assistant").closest("li");
    const aboutEntry = within(navigation).getByText("À propos").closest("li");

    expect(homeEntry).toHaveAttribute("aria-current", "page");
    expect(assistantEntry).not.toBeNull();
    expect(aboutEntry).not.toBeNull();
    expect(within(assistantEntry as HTMLElement).getByText("À venir")).toBeInTheDocument();
    expect(within(aboutEntry as HTMLElement).getByText("À venir")).toBeInTheDocument();
  });

  it("opens and closes the mobile menu", () => {
    render(<App />);

    const openButton = screen.getByRole("button", {
      name: "Ouvrir la navigation",
    });

    expect(openButton).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(openButton);
    expect(openButton).toHaveAttribute("aria-expanded", "true");

    const closeButton = screen.getByRole("button", { name: "Fermer le menu" });
    fireEvent.click(closeButton);
    expect(openButton).toHaveAttribute("aria-expanded", "false");
  });

  it("closes the mobile menu with Escape", () => {
    render(<App />);

    const openButton = screen.getByRole("button", {
      name: "Ouvrir la navigation",
    });

    fireEvent.click(openButton);
    fireEvent.keyDown(document, { key: "Escape" });

    expect(openButton).toHaveAttribute("aria-expanded", "false");
    expect(openButton).toHaveFocus();
  });
});
