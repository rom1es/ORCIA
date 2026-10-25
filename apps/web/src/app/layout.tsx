import "@orcia/ui/styles/tokens.css";
import React from "react";
import { ShellContainer } from "../components/ShellContainer";
import { I18nProvider } from "../i18n";

export const metadata = {
  title: "ORCIA — Orchestration of Processes, Context, and Intelligent Agents",
  description: "Human-Led, Agent-Accelerated Enterprise Process & Context Orchestration",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>
        <I18nProvider initialLocale="fr">
          <ShellContainer>{children}</ShellContainer>
        </I18nProvider>
      </body>
    </html>
  );
}
