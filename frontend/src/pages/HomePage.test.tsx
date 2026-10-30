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
      screen.getByRole("heading", { name: "Comment utiliser SecureBank-AI ?" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Posez votre question" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Connectez-vous" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Consultez la réponse" })).toBeInTheDocument();
  });

  it("identifies the current navigation entry and public about link", () => {
    render(<App />);

    const navigation = screen.getByRole("navigation", {
      name: "Sections de l’application",
    });
    const homeLink = within(navigation).getByRole("link", { name: "Accueil" });
    const assistantLink = within(navigation).getByRole("link", {
      name: "Assistant",
    });
    const aboutLink = within(navigation).getByRole("link", { name: "À propos" });

    expect(homeLink).toHaveAttribute("aria-current", "page");
    expect(assistantLink).not.toHaveAttribute("aria-current");
    expect(aboutLink).toHaveAttribute("href", "/about");
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
