import { useCallback, useEffect, useState } from "react";

import { HomePage } from "../pages/HomePage";
import { AssistantPage } from "../pages/AssistantPage";
import { AppShell } from "../components/AppShell";
import { pageFromPath, pathForPage, type PageId } from "./navigation";

export function App() {
  const [currentPage, setCurrentPage] = useState<PageId>(() =>
    pageFromPath(window.location.pathname),
  );

  useEffect(() => {
    const updatePageFromLocation = () => {
      setCurrentPage(pageFromPath(window.location.pathname));
    };

    window.addEventListener("popstate", updatePageFromLocation);
    return () => {
      window.removeEventListener("popstate", updatePageFromLocation);
    };
  }, []);

  const navigate = useCallback((page: PageId) => {
    const path = pathForPage(page);
    if (window.location.pathname !== path) {
      window.history.pushState({}, "", path);
    }
    setCurrentPage(page);
  }, []);

  const pageTitle = currentPage === "assistant" ? "Assistant" : "Accueil";

  return (
    <AppShell
      currentPage={currentPage}
      onNavigate={navigate}
      pageTitle={pageTitle}
    >
      {currentPage === "assistant" ? <AssistantPage /> : <HomePage />}
    </AppShell>
  );
}
