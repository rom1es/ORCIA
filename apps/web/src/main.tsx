import "@orcia/ui/styles/tokens.css";
import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import React from "react";
import { createRoot } from "react-dom/client";
import { createOrciaQueryClient, createOrciaRouter } from "./router";

export function OrciaSpaApp() {
  const [queryClient] = React.useState(() => createOrciaQueryClient());
  const [router] = React.useState(() => createOrciaRouter({ queryClient }));

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}

const rootElement = typeof document !== "undefined" ? document.getElementById("root") : null;
if (rootElement) {
  createRoot(rootElement).render(
    <React.StrictMode>
      <OrciaSpaApp />
    </React.StrictMode>,
  );
}
