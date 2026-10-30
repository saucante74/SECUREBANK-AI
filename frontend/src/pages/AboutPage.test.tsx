import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { getCurrentUser } from "../api/services";
import { App } from "../app/App";
import i18n, { changeLanguage } from "../i18n";

vi.mock("../api/services", () => ({
  askRag: vi.fn(),
  getCurrentUser: vi.fn(),
  loginUser: vi.fn(),
  logoutUser: vi.fn(),
}));

const getCurrentUserMock = vi.mocked(getCurrentUser);

describe("AboutPage", () => {
  beforeEach(async () => {
    window.history.replaceState({}, "", "/about");
    getCurrentUserMock.mockReset();
    getCurrentUserMock.mockRejectedValue(
      new ApiError({ category: "unauthenticated", method: "GET", status: 401 }),
    );
    await i18n.changeLanguage("fr");
  });

  it("is directly accessible without authentication", async () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "À propos de SecureBank-AI" }),
    ).toBeInTheDocument();
    expect(screen.getByText("SecureBank-AI est un outil d’aide à la recherche d’informations. Il ne remplace pas un conseiller bancaire et ne réalise aucune opération sur vos comptes.")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Se connecter" })).toBeInTheDocument();
  });

  it("opens and closes an FAQ item with its keyboard-operable summary", () => {
    render(<App />);
    const question = screen.getByText("À quoi sert SecureBank-AI ?");
    const details = question.closest("details");

    expect(details).not.toHaveAttribute("open");
    fireEvent.click(question);
    expect(details).toHaveAttribute("open");
    expect(within(details as HTMLElement).getByText(/aide à retrouver et comprendre/)).toBeVisible();
    fireEvent.click(question);
    expect(details).not.toHaveAttribute("open");
  });

  it.each([
    ["fr", "À propos de SecureBank-AI", "Questions fréquentes", "À quoi sert SecureBank-AI ?"],
    ["en", "About SecureBank-AI", "Frequently asked questions", "What is SecureBank-AI for?"],
    ["it", "Informazioni su SecureBank-AI", "Domande frequenti", "A cosa serve SecureBank-AI?"],
    ["de", "Über SecureBank-AI", "Häufig gestellte Fragen", "Wozu dient SecureBank-AI?"],
  ] as const)("translates the public page in %s", async (language, title, faqTitle, firstQuestion) => {
    await changeLanguage(language);
    render(<App />);

    expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: faqTitle })).toBeInTheDocument();
    expect(screen.getByText(firstQuestion)).toBeInTheDocument();
  });
});
