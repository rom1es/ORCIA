import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import {
  writeCachedPlatformAdmin,
  writeCachedPlatformSetupState,
} from "../components/platformSetupStorageHelpers";
import { clearPlatformSetupStorage } from "../components/platformSetupStore";
import { ShellContainer } from "../components/ShellContainer";
import { InboxFeaturePanel } from "../features/inbox";
import { I18nProvider } from "../i18n";
import { isJsdomRuntime } from "../lib/runtimeEnv";
import { getRecordedVitestApiCalls } from "./vitest.setup";

const SRC_ROOT = join(__dirname, "..");
const HELPER = join("lib", "runtimeEnv.ts");

afterEach(() => {
  cleanup();
});

function listSources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    if (name === "__tests__" || name === "generated") return [];
    return statSync(full).isDirectory()
      ? listSources(full)
      : /\.(ts|tsx)$/.test(name)
        ? [full]
        : [];
  });
}

describe("garde jsdom supprimée & transport @orcia/api-client sous Vitest (TEST-03)", () => {
  it("détecte l'environnement jsdom uniquement dans le helper dédié", () => {
    expect(isJsdomRuntime()).toBe(true);
  });

  it("interdit tout court-circuit isJsdomRuntime ou /jsdom/i.test dans le code de production d'apps/web/src", () => {
    const offenders = listSources(SRC_ROOT)
      .filter((file) => relative(SRC_ROOT, file) !== HELPER)
      .filter((file) => {
        const text = readFileSync(file, "utf8");
        return /\/jsdom\/i\.test\(/.test(text) || /\bisJsdomRuntime\b/.test(text);
      })
      .map((file) => relative(SRC_ROOT, file));
    expect(offenders).toEqual([]);
  });

  it("traverse réellement @orcia/api-client (POST/PUT/GET + SSE stream) et réhydrate après vidage de localStorage (vrai F5)", async () => {
    clearPlatformSetupStorage();

    const firstRender = render(
      React.createElement(I18nProvider, {
        initialLocale: "fr",
        children: React.createElement(ShellContainer, {
          children: React.createElement(InboxFeaturePanel),
        }),
      }),
    );

    // 1. Créer le premier administrateur via la modale Jour 0 -> déclenche POST /api/v1/bootstrap/welcome-setup + PUT /api/v1/bootstrap/platform-setup-state
    fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), {
      target: { value: "Claire Admin" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), {
      target: { value: "claire@orcia.io" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-password-input"), {
      target: { value: "OrciaSecure!2026" }, // pragma: allowlist secret
    });
    fireEvent.click(screen.getByTestId("first-boot-admin-submit-btn"));

    // 2. Envoyer un tour à Mon Assistant -> déclenche POST /api/v1/assistant/three-speed/stream (SSE ReadableStream)
    fireEvent.change(screen.getByTestId("assistant-three-speed-input"), {
      target: { value: "Vérifie le transport SSE" },
    });
    fireEvent.click(screen.getByTestId("assistant-three-speed-send-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("assistant-conversation-messages-list").textContent).toContain(
        "Vérifie le transport SSE",
      );
    });

    const callsBeforeReload = getRecordedVitestApiCalls();
    expect(
      callsBeforeReload.some(
        (c) =>
          c.method === "POST" &&
          c.path === "/api/v1/bootstrap/welcome-setup/first-admin",
      ),
    ).toBe(true);
    expect(
      callsBeforeReload.some(
        (c) => c.method === "PUT" && c.path === "/api/v1/bootstrap/platform-setup-state",
      ),
    ).toBe(true);
    expect(
      callsBeforeReload.some(
        (c) => c.method === "POST" && c.path === "/api/v1/assistant/three-speed/stream",
      ),
    ).toBe(true);

    // 3. Simuler un vrai F5 sans cache local : démonter, vider le cache local (sans réinitialiser le backend simulé), puis remonter
    firstRender.unmount();
    writeCachedPlatformAdmin(null);
    writeCachedPlatformSetupState(null);

    render(
      React.createElement(I18nProvider, {
        initialLocale: "fr",
        children: React.createElement(ShellContainer, {
          children: React.createElement(InboxFeaturePanel),
        }),
      }),
    );

    // La réhydratation par GET /api/v1/bootstrap/accostage-status restaure Claire Admin et ferme la modale Jour 0
    await waitFor(() => {
      expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
      expect(screen.getByTestId("user-account-dropdown-trigger").textContent).toContain(
        "Claire Admin",
      );
    });
  });
});
