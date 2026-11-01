import { useDemoUser } from "./auth/DemoUserContext";
import { AppHeader } from "./components/AppHeader";
import { AskPanel } from "./components/AskPanel";
import { DocumentsPanel } from "./components/DocumentsPanel";

export function App() {
  const { user } = useDemoUser();

  return (
    <>
      <a href="#main" className="skip-link">
        Saltar al contenido
      </a>
      <AppHeader />
      <main id="main" className="layout">
        <DocumentsPanel key={`documents-${user.token}`} />
        <AskPanel key={`ask-${user.token}`} />
      </main>
    </>
  );
}
