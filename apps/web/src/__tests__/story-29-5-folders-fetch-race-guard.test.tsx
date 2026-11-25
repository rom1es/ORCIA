import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearAssistantFoldersAndPrefsStorage,
  readSavedAssistantFolders,
} from "../features/inbox/assistantFoldersAndPrefsStore";
import { useServerAssistantFolders } from "../features/inbox/useServerAssistantFolders";

const testMessages = {
  workspaceRequired: "workspace required",
  loadFailed: (detail: string) => `load failed: ${detail}`,
  saveFailed: (detail: string) => `save failed: ${detail}`,
};

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("useServerAssistantFolders race condition guard", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    clearAssistantFoldersAndPrefsStorage();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    clearAssistantFoldersAndPrefsStorage();
  });

  it("preserves a newly created folder when an older GET overview resolves later with empty folders", async () => {
    const delayedOverview = createDeferred<Response>();
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const method = (init?.method ?? "GET").toUpperCase();
      if (method === "GET" && url.includes("/api/v1/assistant/workspaces/ws-race-1/overview")) {
        return delayedOverview.promise;
      }
      if (method === "POST" && url.endsWith("/api/v1/assistant/folders")) {
        return jsonResponse({
          folder_id: "folder-created-1",
          title: "Verified Citations Folder",
          pinned_notes_markdown: "",
          consolidated_summary: "",
          visibility_mode: "PRIVATE",
          has_restricted_sources: false,
          assembled_layer5_prompt_block: "",
        });
      }
      throw new Error(`Unexpected fetch: ${method} ${url}`);
    }) as typeof fetch;

    const onFeedback = vi.fn();
    const { result } = renderHook(() =>
      useServerAssistantFolders({ workspaceId: "ws-race-1", messages: testMessages, onFeedback }),
    );

    let createdId: string | null = null;
    await act(async () => {
      const created = await result.current.createFolder("Verified Citations Folder");
      createdId = created?.folderId ?? null;
    });

    expect(createdId).toBe("folder-created-1");
    expect(result.current.folders.map((f) => f.folderId)).toEqual(["folder-created-1"]);

    // Resolve the stale pre-mutation GET overview after POST /folders already succeeded.
    await act(async () => {
      delayedOverview.resolve(jsonResponse({ workspace_id: "ws-race-1", folders: [], threads: [] }));
      await delayedOverview.promise;
    });

    expect(result.current.folders.map((f) => f.folderId)).toEqual(["folder-created-1"]);
    expect(result.current.folders[0]?.title).toBe("Verified Citations Folder");
    expect(readSavedAssistantFolders().map((f) => f.folderId)).toEqual(["folder-created-1"]);
    expect(onFeedback).not.toHaveBeenCalled();
  });

  it("merges non-mutated server folders while preserving concurrent pinned notes and visibility edits", async () => {
    const delayedOverview = createDeferred<Response>();
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const method = (init?.method ?? "GET").toUpperCase();
      if (method === "GET" && url.includes("/api/v1/assistant/workspaces/ws-race-2/overview")) {
        return delayedOverview.promise;
      }
      if (method === "POST" && url.endsWith("/api/v1/assistant/folders")) {
        const body = JSON.parse(String(init?.body ?? "{}")) as {
          folder_id?: string;
          title: string;
          pinned_notes_markdown?: string;
        };
        return jsonResponse({
          folder_id: body.folder_id ?? "folder-local-2",
          title: body.title,
          pinned_notes_markdown: body.pinned_notes_markdown ?? "",
          consolidated_summary: "",
          visibility_mode: "PRIVATE",
          has_restricted_sources: false,
          assembled_layer5_prompt_block: "",
        });
      }
      if (method === "POST" && url.includes("/api/v1/assistant/folders/folder-local-2/share")) {
        return jsonResponse({
          folder_id: "folder-local-2",
          visibility_mode: "WORKSPACE_OPEN",
        });
      }
      throw new Error(`Unexpected fetch: ${method} ${url}`);
    }) as typeof fetch;

    const onFeedback = vi.fn();
    const { result } = renderHook(() =>
      useServerAssistantFolders({ workspaceId: "ws-race-2", messages: testMessages, onFeedback }),
    );

    await act(async () => {
      await result.current.createFolder("Audit Notes");
    });
    const created = result.current.folders.find((f) => f.title === "Audit Notes");
    if (!created) throw new Error("Expected folder to be created");

    await act(async () => {
      await result.current.savePinnedNotes(created, "Updated pinned context");
    });
    const updated = result.current.folders.find((f) => f.folderId === created.folderId);
    if (!updated) throw new Error("Expected updated folder in state");

    await act(async () => {
      await result.current.changeVisibility(updated, "WORKSPACE_OPEN");
    });

    // Stale overview contains an older snapshot of folder-local-2 plus an existing server folder.
    await act(async () => {
      delayedOverview.resolve(
        jsonResponse({
          workspace_id: "ws-race-2",
          folders: [
            {
              folder_id: "folder-local-2",
              title: "Audit Notes",
              pinned_notes_markdown: "",
              consolidated_summary: "",
              visibility_mode: "PRIVATE",
            },
            {
              folder_id: "folder-existing-server",
              title: "Preexisting Server Folder",
              pinned_notes_markdown: "Server note",
              consolidated_summary: "",
              visibility_mode: "SHARED_SELECTED",
            },
          ],
          threads: [],
        }),
      );
      await delayedOverview.promise;
    });

    const localEdited = result.current.folders.find((f) => f.folderId === "folder-local-2");
    const serverExisting = result.current.folders.find((f) => f.folderId === "folder-existing-server");
    expect(localEdited?.pinnedNotesMarkdown).toBe("Updated pinned context");
    expect(localEdited?.visibilityMode).toBe("WORKSPACE_OPEN");
    expect(serverExisting?.title).toBe("Preexisting Server Folder");
    expect(onFeedback).not.toHaveBeenCalled();
  });

  it("ignores stale responses from a previous workspace after workspaceId changes", async () => {
    const wsAlphaOverview = createDeferred<Response>();
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const method = (init?.method ?? "GET").toUpperCase();
      if (method === "GET" && url.includes("/api/v1/assistant/workspaces/ws-alpha/overview")) {
        return wsAlphaOverview.promise;
      }
      if (method === "GET" && url.includes("/api/v1/assistant/workspaces/ws-beta/overview")) {
        return jsonResponse({
          workspace_id: "ws-beta",
          folders: [
            {
              folder_id: "folder-beta-1",
              title: "Beta Folder",
              pinned_notes_markdown: "",
              consolidated_summary: "",
              visibility_mode: "PRIVATE",
            },
          ],
          threads: [],
        });
      }
      throw new Error(`Unexpected fetch: ${method} ${url}`);
    }) as typeof fetch;

    const onFeedback = vi.fn();
    const { result, rerender } = renderHook(
      ({ wsId }: { wsId: string }) =>
        useServerAssistantFolders({ workspaceId: wsId, messages: testMessages, onFeedback }),
      { initialProps: { wsId: "ws-alpha" } },
    );

    rerender({ wsId: "ws-beta" });
    await waitFor(() => expect(result.current.folders.map((f) => f.folderId)).toEqual(["folder-beta-1"]));

    // Late ws-alpha overview must be discarded completely.
    await act(async () => {
      wsAlphaOverview.resolve(
        jsonResponse({
          workspace_id: "ws-alpha",
          folders: [
            {
              folder_id: "folder-alpha-stale",
              title: "Stale Alpha Folder",
              pinned_notes_markdown: "",
              consolidated_summary: "",
              visibility_mode: "PRIVATE",
            },
          ],
          threads: [],
        }),
      );
      await wsAlphaOverview.promise;
    });

    expect(result.current.folders.map((f) => f.folderId)).toEqual(["folder-beta-1"]);
    expect(onFeedback).not.toHaveBeenCalled();
  });
});
