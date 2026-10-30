import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

import i18n from "../i18n";

afterEach(async () => {
  cleanup();
  window.history.replaceState({}, "", "/");
  window.localStorage.clear();
  document.cookie = "securebank_csrf=; Max-Age=0; path=/";
  await i18n.changeLanguage("fr");
});
