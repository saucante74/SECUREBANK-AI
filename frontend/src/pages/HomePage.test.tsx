import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HomePage } from "./HomePage";

describe("HomePage", () => {
  it("displays the initial SecureBank-AI content", () => {
    render(<HomePage />);

    expect(screen.getByText("SecureBank-AI")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Assistant bancaire intelligent et sécurisé",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Interface en préparation")).toBeInTheDocument();
  });
});
