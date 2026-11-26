import { describe, expect, it, vi } from "vitest";
import {
  createOrciaApiClient,
  extractDraftPackReferences,
  extractMissingClosureDependencies,
  extractMissingSlotsFromProblem,
  extractPackLeakFindings,
  OrciaProblemError,
} from "../index";

function jsonResp(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("Story 31.6 — @orcia/api-client Packs Domain & Guarded Delete Wrappers", () => {
  it("calls workspace pack activation, reorder, slot bindings, and run lock routes", async () => {
    const calls: Array<{ url: string; method: string; body?: string }> = [];
    const fetchMock: typeof fetch = vi.fn(async (input, init) => {
      const url = typeof input === "string" ? input : input.toString();
      calls.push({
        url,
        method: init?.method ?? "GET",
        body: typeof init?.body === "string" ? init.body : undefined,
      });
      if (url.endsWith("/slots")) {
        return jsonResp({ workspace_id: "ws-1", pack_slug: "sdlc", slot_bindings: [], trace_id: "t" });
      }
      if (url.endsWith("/lock")) {
        return jsonResp({
          run_id: "run-1",
          workspace_id: "ws-1",
          pinned_packs: [],
          resolved_pack_slots: [],
          manifest_sha256: "a".repeat(64),
          trace_id: "t",
        });
      }
      return jsonResp({ workspace_id: "ws-1", packs: [], trace_id: "t" });
    }) as typeof fetch;

    const client = createOrciaApiClient({ baseUrl: "", fetchImpl: fetchMock, locale: "en" });
    await client.listWorkspacePacks("ws-1");
    await client.activateWorkspacePack("ws-1", "sdlc", { version: "1.0.0" });
    await client.reorderWorkspacePacks("ws-1", { ordered_pack_slugs: ["orcia-docs", "sdlc"] });
    await client.bindWorkspacePackSlots("ws-1", "sdlc", {
      bindings: [{ slot_key: "git_repo", target_kind: "WORKSPACE_DATASOURCE", target_id: "ds-1" }],
    });
    await client.deactivateWorkspacePack("ws-1", "sdlc");
    await client.getWorkflowV2RunLock("run-1");

    expect(calls.map((c) => `${c.method} ${c.url}`)).toEqual([
      "GET /api/v1/workspaces/ws-1/packs",
      "POST /api/v1/workspaces/ws-1/packs/sdlc/activate",
      "PUT /api/v1/workspaces/ws-1/packs/reorder",
      "PUT /api/v1/workspaces/ws-1/packs/sdlc/slots",
      "DELETE /api/v1/workspaces/ws-1/packs/sdlc/deactivate",
      "GET /api/v1/runs/run-1/lock",
    ]);
  });

  it("uploads multipart .zip pack, manages composer drafts, and exports scrubbed zip", async () => {
    const calls: Array<{ url: string; method: string; isFormData: boolean }> = [];
    const fetchMock: typeof fetch = vi.fn(async (input, init) => {
      const url = typeof input === "string" ? input : input.toString();
      calls.push({
        url,
        method: init?.method ?? "GET",
        isFormData: typeof FormData !== "undefined" && init?.body instanceof FormData,
      });
      if (url.includes("/export")) {
        return new Response(new Blob(["PK\x05\x06"]), {
          status: 200,
          headers: {
            "Content-Type": "application/zip",
            "Content-Disposition": 'attachment; filename="custom-0.1.0.zip"',
          },
        });
      }
      return jsonResp({ bundle_id: "b-1", slug: "custom", name: "Custom", version: "0.1.0", deleted: true });
    }) as typeof fetch;

    const client = createOrciaApiClient({ baseUrl: "", fetchImpl: fetchMock });
    const file = new Blob(["zip-bytes"], { type: "application/zip" });
    await client.importPackArchiveFile({
      file,
      filename: "custom.zip",
      scopeType: "WORKSPACE",
      scopeId: "ws-1",
      replaceDraft: true,
    });
    await client.createPackDraft({
      slug: "custom",
      name: "Custom",
      scope_type: "WORKSPACE",
      scope_id: "ws-1",
    });
    await client.setPackDraftMembers("b-1", { members: [{ entity_type: "AGENT", entity_id: "a-1" }] });
    await client.publishPackDraft("b-1", { auto_include_dependencies: true });
    const zip = await client.exportPackDraftZip("b-1", { auto_include_dependencies: true });
    expect(zip.filename).toBe("custom-0.1.0.zip");
    await client.deletePackDraft("b-1");

    expect(calls[0]).toEqual({
      url: "POST".startsWith("POST") ? "/api/v1/packs/import" : "",
      method: "POST",
      isFormData: true,
    });
    expect(calls.map((c) => `${c.method} ${c.url}`)).toContain(
      "POST /api/v1/packs/composer/b-1/publish?auto_include_dependencies=true",
    );
    expect(calls.map((c) => `${c.method} ${c.url}`)).toContain(
      "POST /api/v1/packs/composer/b-1/export?auto_include_dependencies=true",
    );
  });

  it("passes unlink_from_draft_packs=true on agent, skill, workflow, and VSM deletes and parses problem payloads", async () => {
    const urls: string[] = [];
    const fetchMock: typeof fetch = vi.fn(async (input) => {
      urls.push(typeof input === "string" ? input : input.toString());
      return jsonResp({ deleted: true });
    }) as typeof fetch;

    const client = createOrciaApiClient({ baseUrl: "", fetchImpl: fetchMock });
    await client.deleteAgent("a-1", { unlinkFromDraftPacks: true });
    await client.deleteSkill("s-1", { unlinkFromDraftPacks: true });
    await client.deleteWorkflowV2("wf-1", { unlinkFromDraftPacks: true });
    await client.deleteVsmV2("vsm-1", { unlinkFromDraftPacks: true });

    expect(urls).toEqual([
      "/api/v1/agents-and-skills/agents/a-1?unlink_from_draft_packs=true",
      "/api/v1/agents-and-skills/skills/s-1?unlink_from_draft_packs=true",
      "/api/v1/workflows/v2/wf-1?unlink_from_draft_packs=true",
      "/api/v1/vsm/vsm-1?unlink_from_draft_packs=true",
    ]);

    const err409 = new OrciaProblemError({
      type: "about:blank",
      title: "Conflict",
      status: 409,
      detail: "Referenced",
      error_code: "ERR_ENTITY_REFERENCED_BY_PACK_DRAFT",
      trace_id: "0".repeat(32),
      draft_packs: [{ bundle_id: "d-1", slug: "pack-a", name: "Pack A", version: "0.1.0" }],
      missing_dependencies: [{ entity_type: "SKILL", entity_id: "sk-1", reason: "missing", referenced_by: "a-1" }],
      leak_findings: [{ path: "apm.yml", kind: "PII_EMAIL", detail: "email" }],
    });
    expect(extractDraftPackReferences(err409)).toEqual([
      { bundleId: "d-1", slug: "pack-a", name: "Pack A", version: "0.1.0" },
    ]);
    expect(extractMissingClosureDependencies(err409)).toHaveLength(1);
    expect(extractPackLeakFindings(err409)).toHaveLength(1);

    const err422 = new OrciaProblemError({
      type: "about:blank",
      title: "Unbound",
      status: 422,
      detail: "Required pack slot(s) unbound for sdlc: git_repo, jira_project",
      error_code: "ERR_PACK_SLOT_UNBOUND",
      trace_id: "0".repeat(32),
    });
    expect(extractMissingSlotsFromProblem(err422)).toEqual(["git_repo", "jira_project"]);
  });
});
