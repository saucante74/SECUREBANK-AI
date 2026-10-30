import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { HomePage } from "../pages/HomePage";
import { AssistantPage } from "../pages/AssistantPage";
import { AboutPage } from "../pages/AboutPage";
import { EvaluationPage } from "../pages/EvaluationPage";
import { AppShell } from "../components/AppShell";
import { useAuthSession } from "../hooks/useAuthSession";
import { pageFromPath, pathForPage, type PageId } from "./navigation";

export function App() {
  const { t } = useTranslation();
  const auth = useAuthSession();
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

  useEffect(() => {
    if (
      currentPage === "evaluation" &&
      auth.status !== "checking" &&
      auth.user?.role !== "admin"
    ) {
      window.history.replaceState({}, "", "/");
    }
  }, [auth.status, auth.user?.role, currentPage]);

  const accessiblePage =
    currentPage === "evaluation" && auth.user?.role !== "admin"
      ? "home"
      : currentPage;
  const pageTitle = t(`navigation.${accessiblePage}`);

  const pageContent =
    accessiblePage === "assistant" ? (
      <AssistantPage
        key={auth.clearVersion}
        authStatus={auth.status}
        onLogin={auth.login}
        onSessionExpired={auth.expireSession}
      />
    ) : accessiblePage === "evaluation" ? (
      <EvaluationPage onSessionExpired={auth.expireSession} />
    ) : accessiblePage === "about" ? (
      <AboutPage />
    ) : (
      <HomePage />
    );

  return (
    <AppShell
      authStatus={auth.status}
      currentPage={accessiblePage}
      logoutErrorKey={auth.logoutErrorKey}
      onLogin={auth.login}
      onNavigate={navigate}
      onLogout={auth.logout}
      pageTitle={pageTitle}
      user={auth.user}
    >
      {pageContent}
    </AppShell>
  );
}
