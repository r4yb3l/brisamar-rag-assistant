import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { DemoUserProvider } from "./auth/DemoUserContext";
import { createQueryClient } from "./queryClient";
import "./styles.css";

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("Root element #root not found");

const queryClient = createQueryClient();

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <DemoUserProvider>
        <App />
      </DemoUserProvider>
    </QueryClientProvider>
  </StrictMode>,
);
