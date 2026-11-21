import http from "node:http";
import type { AddressInfo } from "node:net";
import { expect, type Page } from "@playwright/test";

export function startLocalLlmCassetteServer(): Promise<{
  baseUrl: string;
  slowFailBaseUrl: string;
  close: () => Promise<void>;
}> {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const url = req.url ?? "";
      if (url.startsWith("/slow-fail/")) {
        setTimeout(() => {
          res.statusCode = 500;
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ error: { message: "Simulated provider failure 500" } }));
        }, 700);
        return;
      }
      res.setHeader("Content-Type", "application/json");
      if (url.endsWith("/models")) {
        res.end(
          JSON.stringify({
            object: "list",
            data: [{ id: "qwen2.5:14b" }, { id: "bge-m3:latest" }],
          }),
        );
        return;
      }
      if (url.endsWith("/embeddings")) {
        res.end(
          JSON.stringify({
            object: "list",
            model: "bge-m3:latest",
            data: [{ object: "embedding", index: 0, embedding: Array(1024).fill(0.01) }],
          }),
        );
        return;
      }
      res.end(
        JSON.stringify({
          id: "chatcmpl-e2e",
          object: "chat.completion",
          choices: [
            { index: 0, message: { role: "assistant", content: "OK" }, finish_reason: "stop" },
          ],
        }),
      );
    });
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address() as AddressInfo;
      resolve({
        baseUrl: `http://127.0.0.1:${addr.port}/v1`,
        slowFailBaseUrl: `http://127.0.0.1:${addr.port}/slow-fail/v1`,
        close: () => new Promise<void>((done) => server.close(() => done())),
      });
    });
  });
}

export async function createOllamaAiModelViaModal(
  page: Page,
  params: {
    readonly displayName: string;
    readonly modelId: string;
    readonly endpointUrl: string;
    readonly usage?: "chat" | "embedding";
    readonly saveAndTest?: boolean;
  },
): Promise<void> {
  await page.getByTestId("open-create-ai-model-modal-btn").click();
  await page.getByTestId("ai-model-config-modal").getByTestId("llm-provider-preset-ollama").click();
  if (params.usage === "embedding") {
    await page.getByTestId("ai-model-usage-embedding-btn").click();
  }
  await page.getByTestId("ai-model-display-name-input").fill(params.displayName);
  await page.getByTestId("ai-model-primary-model-input").fill(params.modelId);
  await page.getByTestId("ai-model-endpoint-uri-input").fill(params.endpointUrl);
  await page.getByTestId("ai-model-auth-mode-select").selectOption("none_local");
  const submitTestId = params.saveAndTest ? "save-and-test-ai-model-btn" : "save-ai-model-btn";
  await page.getByTestId(submitTestId).click();
  await expect(page.getByTestId("ai-model-display-name-input")).toBeHidden({ timeout: 15000 });
}

export async function deleteAiModelAndAssertRemoved(page: Page, modelId: string): Promise<void> {
  await page.getByTestId(`ai-model-row-actions-${modelId}-trigger`).click();
  await page.getByTestId(`delete-ai-model-item-${modelId}`).click();
  await expect(page.getByTestId("ai-model-delete-dialog")).toBeVisible({ timeout: 10000 });
  const confirmBtn = page.getByTestId("confirm-delete-ai-model-btn");
  await expect(confirmBtn).toBeEnabled({ timeout: 10000 });
  await Promise.all([
    page.waitForResponse(
      (res) =>
        res.url().includes(`/api/v1/settings/ai-models/mappings/${modelId}`) &&
        res.request().method() === "DELETE",
      { timeout: 15000 },
    ),
    confirmBtn.click(),
  ]);
  await expect(page.getByTestId(`llm-tier-row-${modelId}`)).toHaveCount(0);
}

export async function registerGitLabConnectorAndAssertBadge(
  page: Page,
  adminSecretPlaceholder: string,
): Promise<string> {
  await page.getByTestId("connector-kind-select").selectOption("GITLAB");
  await page.getByTestId("connector-name-input").fill("GitLab Entreprise E2E");
  await page.getByTestId("connector-base-url-input").fill("https://gitlab.e2e.internal");
  await page.getByTestId("connector-auth-mode-select").selectOption("OAUTH2_PASSTHROUGH");
  await page.getByTestId("connector-admin-secret-input").fill(adminSecretPlaceholder);
  await Promise.all([
    page.waitForResponse(
      (res) =>
        res.url().includes("/api/v1/settings/connectors") && res.request().method() === "POST",
      { timeout: 15000 },
    ),
    page.getByTestId("register-connector-submit-btn").click(),
  ]);

  const connectorRow = page.locator("[data-testid^='enterprise-connector-row-']").first();
  await expect(connectorRow).toBeVisible({ timeout: 15000 });
  const rowTestId = (await connectorRow.getAttribute("data-testid")) ?? "";
  const connectorId = rowTestId.replace("enterprise-connector-row-", "");
  await expect(page.getByTestId(`connector-secret-badge-${connectorId}`)).toBeVisible();
  await expect(page.getByTestId("settings-connectors-section")).not.toContainText(
    adminSecretPlaceholder,
  );
  return connectorId;
}
