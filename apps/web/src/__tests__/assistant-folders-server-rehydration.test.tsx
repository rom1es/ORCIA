import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useServerAssistantFolders } from "../features/inbox/useServerAssistantFolders";
import { getRecordedVitestApiCalls } from "./vitest.setup";

/** Simule le F5 « à froid » : cache navigateur vidé quand l'environnement de test en fournit un. */
function clearBrowserCache(): void {
  const storage = window.localStorage as Partial<Storage> | undefined;
  if (typeof storage?.clear === "function") storage.clear();
}

const messages = {
  workspaceRequired: "espace requis",
  loadFailed: (d: string) => `chargement impossible: ${d}`,
  saveFailed: (d: string) => `enregistrement impossible: ${d}`,
};

describe("Dossiers de Mon Assistant — serveur source de vérité et survie au F5 (BUG-E2E-01)", () => {
  it("réhydrate depuis l'API après démontage et localStorage vidé", async () => {
    const onFeedback = vi.fn();
    const first = renderHook(() => useServerAssistantFolders({ workspaceId: "ws-real-1", messages, onFeedback }));
    await act(async () => {
      await first.result.current.createFolder("Dossier persistant");
    });
    const created = first.result.current.folders.find((f) => f.title === "Dossier persistant");
    expect(created?.folderId).toMatch(/^folder-/);
    first.unmount();

    clearBrowserCache();
    const second = renderHook(() => useServerAssistantFolders({ workspaceId: "ws-real-1", messages, onFeedback }));
    await waitFor(() => expect(second.result.current.folders.map((f) => f.title)).toContain("Dossier persistant"));
    expect(getRecordedVitestApiCalls().some((c) => c.method === "GET" && c.path === "/api/v1/assistant/workspaces/ws-real-1/overview")).toBe(true);
    expect(onFeedback).not.toHaveBeenCalled();
  });

  it("refuse la création sans espace actif, sans appel API ni espace de repli fictif", async () => {
    const onFeedback = vi.fn();
    const { result } = renderHook(() => useServerAssistantFolders({ workspaceId: "", messages, onFeedback }));
    let saved: unknown = "unset";
    await act(async () => {
      saved = await result.current.createFolder("Sans espace");
    });
    expect(saved).toBeNull();
    expect(onFeedback).toHaveBeenCalledWith("espace requis");
    expect(getRecordedVitestApiCalls().some((c) => c.path === "/api/v1/assistant/folders")).toBe(false);
  });

  it("persiste les notes et la visibilité côté serveur", async () => {
    const onFeedback = vi.fn();
    const first = renderHook(() => useServerAssistantFolders({ workspaceId: "ws-real-2", messages, onFeedback }));
    await act(async () => {
      await first.result.current.createFolder("Notes");
    });
    const folder = first.result.current.folders[first.result.current.folders.length - 1];
    if (!folder) throw new Error("dossier non créé");
    await act(async () => {
      await first.result.current.savePinnedNotes(folder, "Contexte métier");
    });
    const withNotes = first.result.current.folders.find((f) => f.folderId === folder.folderId);
    if (!withNotes) throw new Error("dossier perdu");
    await act(async () => {
      await first.result.current.changeVisibility(withNotes, "WORKSPACE_OPEN");
    });
    first.unmount();

    clearBrowserCache();
    const second = renderHook(() => useServerAssistantFolders({ workspaceId: "ws-real-2", messages, onFeedback }));
    await waitFor(() => {
      const reloaded = second.result.current.folders.find((f) => f.folderId === folder.folderId);
      expect(reloaded?.pinnedNotesMarkdown).toBe("Contexte métier");
      expect(reloaded?.visibilityMode).toBe("WORKSPACE_OPEN");
    });
  });

  it("remonte explicitement une erreur de chargement (aucun catch silencieux)", async () => {
    const onFeedback = vi.fn();
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async () => new Response("boom", { status: 500 })) as typeof fetch;
    try {
      renderHook(() => useServerAssistantFolders({ workspaceId: "ws-down", messages, onFeedback }));
      await waitFor(() => expect(onFeedback).toHaveBeenCalledTimes(1));
      expect(String(onFeedback.mock.calls[0]?.[0])).toMatch(/^chargement impossible/);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
