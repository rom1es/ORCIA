import { expect, test } from "@playwright/test";
import { resetDay0 } from "./support/day0";

test.describe("Socle E2E bi-serveur (TEST-01 & Stories 16.1–16.2 Reflexive Harness)", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("l'API FastAPI répond via le proxy Vite (Navigateur → Vite → FastAPI)", async ({
    request,
  }) => {
    const response = await request.get("/api/v1/health");
    expect(response.status()).toBe(200);
    const body = (await response.json()) as Record<string, unknown>;
    expect(JSON.stringify(body)).toContain("ok");
  });

  test("après reset Jour 0 la modale de premier administrateur est présentée", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page.getByTestId("first-boot-admin-setup-modal")).toBeVisible({
      timeout: 30000,
    });
  });

  test("Story 16.1 — l'inspection chirurgicale #L1-40 retourne 40 lignes badge Y et bloque ../ en RFC 9457", async ({
    request,
  }) => {
    const sliceResp = await request.get(
      "/api/v1/sources/inspect-lines?uri=docs/product/capabilities.yaml&start_line=1&end_line=40",
    );
    expect(sliceResp.status()).toBe(200);
    const sliceBody = (await sliceResp.json()) as {
      file_badge_code: string;
      formatted_badge: string;
      lines: Array<{ line_number: number; content: string }>;
      redacted: boolean;
    };
    expect(sliceBody.file_badge_code).toBe("Y");
    expect(sliceBody.formatted_badge).toBe("Analyzed Y capabilities.yaml #L1-40");
    expect(sliceBody.redacted).toBe(false);
    expect(sliceBody.lines).toHaveLength(40);
    expect(sliceBody.lines[0]?.line_number).toBe(1);
    expect(sliceBody.lines[39]?.line_number).toBe(40);

    const traversalResp = await request.get(
      "/api/v1/sources/inspect-lines?uri=../pyproject.toml&start_line=1&end_line=10",
    );
    expect([400, 422]).toContain(traversalResp.status());
    expect(traversalResp.headers()["content-type"]).toContain("application/problem+json");
    const problem = (await traversalResp.json()) as { error_code?: string; trace_id?: string };
    expect(problem.error_code).toBe("ERR_VALIDATION_FAILED");
    expect(Boolean(problem.trace_id)).toBe(true);
  });

  test("Story 16.2 — moteur réflexif asyncio, survie F5 WAITING_WRITE_PREVIEW, approbation WritePreviewCard et flux SSE", async ({
    request,
  }) => {
    const startResp = await request.post("/api/v1/executions/reflexive", {
      data: {
        actor_slug: "assistant-agent",
        objective: "Analyser capabilities.yaml et préparer une publication gouvernée",
        effort_mode: "approfondi",
        initial_resources: ["docs/product/capabilities.yaml"],
        requested_write_preview: {
          connector_type: "mcp:default",
          action: "publish_note",
          target_resource_uri: "catalog://docs/e2e-reflexive-note",
          action_summary: "Publier la note de synthèse E2E",
          payload: { markdown: "# Synthèse E2E\n- Ligne 1\n- Ligne 2" },
        },
      },
    });
    expect(startResp.status()).toBe(200);
    const paused = (await startResp.json()) as {
      execution_id: string;
      status: string;
      max_turns: number;
      max_budget_tokens: number;
      pending_write_preview: { preview_id: string; payload_sha256: string } | null;
    };
    expect(paused.status).toBe("WAITING_WRITE_PREVIEW");
    expect(paused.max_turns).toBe(25);
    expect(paused.max_budget_tokens).toBe(48000);
    expect(paused.pending_write_preview).not.toBeNull();
    const previewId = paused.pending_write_preview?.preview_id ?? "";
    expect(previewId.length).toBeGreaterThan(0);

    const rehydratedResp = await request.get(`/api/v1/executions/${paused.execution_id}`);
    expect(rehydratedResp.status()).toBe(200);
    const rehydrated = (await rehydratedResp.json()) as {
      status: string;
      pending_write_preview: { preview_id: string } | null;
    };
    expect(rehydrated.status).toBe("WAITING_WRITE_PREVIEW");
    expect(rehydrated.pending_write_preview?.preview_id).toBe(previewId);

    const approveResp = await request.post(
      `/api/v1/executions/${paused.execution_id}/approve-write`,
      {
        data: {
          approved: true,
          preview_id: previewId,
        },
      },
    );
    expect(approveResp.status()).toBe(200);
    const completed = (await approveResp.json()) as {
      status: string;
      artifact_pointer: { sha256: string; s3_uri: string } | null;
    };
    expect(completed.status).toBe("COMPLETED");
    expect(completed.artifact_pointer?.sha256).toHaveLength(64);

    const sseResp = await request.get(`/api/v1/executions/${paused.execution_id}/trace-stream`);
    expect(sseResp.status()).toBe(200);
    expect(sseResp.headers()["content-type"]).toContain("text/event-stream");
    const sseText = await sseResp.text();
    expect(sseText).toContain("event: file_analyzed");
    expect(sseText).toContain("event: write_preview_requested");
    expect(sseText).toContain("event: answer_token_delta");
    expect(sseText).toContain("event: loop_completed");
  });
});
