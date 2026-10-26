import { HomePage } from "../pages/HomePage";
import { AppShell } from "../components/AppShell";

export function App() {
  return (
    <AppShell pageTitle="Accueil">
      <HomePage />
    </AppShell>
  );
}
