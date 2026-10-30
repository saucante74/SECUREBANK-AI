import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { HomePage } from "../pages/HomePage";
import { AssistantPage } from "../pages/AssistantPage";
import { AboutPage } from "../pages/AboutPage";
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

  const pageTitle = t(`navigation.${currentPage}`);

  const pageContent =
    currentPage === "assistant" ? (
      <AssistantPage
        key={auth.clearVersion}
        authStatus={auth.status}
        onLogin={auth.login}
        onSessionExpired={auth.expireSession}
      />
    ) : currentPage === "about" ? (
      <AboutPage />
    ) : (
      <HomePage />
    );

  return (
    <AppShell
      authStatus={auth.status}
      currentPage={currentPage}
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
