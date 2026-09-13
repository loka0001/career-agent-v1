import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import { AppErrorBoundary } from "./app/AppErrorBoundary";
import { ThemeProvider } from "./app/ThemeContext";
import { LanguageProvider } from "./i18n";
import "@fontsource-variable/manrope";
import "@fontsource-variable/jetbrains-mono";
import "@fontsource/ibm-plex-sans-arabic/400.css";
import "@fontsource/ibm-plex-sans-arabic/500.css";
import "@fontsource/ibm-plex-sans-arabic/600.css";
import "@fontsource/ibm-plex-sans-arabic/700.css";
import "./styles/tokens.css";
import "./styles/globals.css";

const root = document.getElementById("root");
if (!root) throw new Error("Root element is missing");
createRoot(root).render(
  <StrictMode>
    <ThemeProvider>
      <LanguageProvider>
        <AppErrorBoundary>
          <App />
        </AppErrorBoundary>
      </LanguageProvider>
    </ThemeProvider>
  </StrictMode>,
);
