/** @uj UJ-7, UJ-15 | @cap CAP-003, CAP-052, CAP-053, CAP-054, CAP-190 */
import http from "node:http";
import type { AddressInfo } from "node:net";
import { expect, test } from "./support/e2eCaptureFixture";
import { resetDay0 } from "./support/day0";
import { expectDbRowExists } from "./support/dbAssertions";
import {
  bootstrapAdminSession,
  getBearerTokenFromSession,
  openSettingsTabViaUi,
  openUserSettingsTab,
} from "./support/authAndOrgHelpers";

function startLocalLlmCassetteServer(): Promise<{ baseUrl: string; close: () => Promise<void> }> {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const url = req.url ?? "";
      res.setHeader("Content-Type", "application/json");
      if (url.endsWith("/models")) {
        res.end(JSON.stringify({ object: "list", data: [{ id: "qwen2.5:14b" }, { id: "bge-m3:latest" }] }));
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
          choices: [{ index: 0, message: { role: "assistant", content: "OK" }, finish_reason: "stop" }],
        }),
      );
    });
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address() as AddressInfo;
      resolve({
        baseUrl: `http://127.0.0.1:${addr.port}/v1`,
        close: () => new Promise<void>((done) => server.close(() => done())),
      });
    });
  });
}

test.describe("Hub modèles IA, réindexation sémantique, connecteurs et Permission Broker", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("Jour 0 sans embedding, garde SSRF, modèles Chat/Embedding 1024 et réindexation survivent à F5", async ({
    page,
  }) => {
    const mockLlm = await startLocalLlmCassetteServer();
    try {
      await bootstrapAdminSession(page);

      await page.goto("/assistant");
      await expect(page.getByTestId("assistant-no-embedding-banner")).toBeVisible({ timeout: 20000 });

      await openSettingsTabViaUi(page, "models");
      await expect(page.getByTestId("ai-models-empty-state")).toBeVisible({ timeout: 15000 });

      await page.getByTestId("open-create-ai-model-modal-btn").click();
      await expect(page.getByTestId("ai-model-display-name-input")).toHaveValue("");
      await expect(page.getByTestId("ai-model-primary-model-input")).toHaveValue("");

      await page.getByTestId("llm-provider-preset-ollama").click();
      await page.getByTestId("ai-model-display-name-input").fill("SSRF Probe");
      await page.getByTestId("ai-model-primary-model-input").fill("qwen2.5:14b");
      await page
        .getByTestId("ai-model-endpoint-uri-input")
        .fill("http://169.254.169.254/latest/meta-data/");
      await page.getByTestId("ai-model-auth-mode-select").selectOption("none_local");
      await page.getByTestId("save-ai-model-btn").click();
      await expect(page.getByTestId("ai-model-config-error")).toBeVisible({ timeout: 10000 });

      await page.getByTestId("ai-model-display-name-input").fill("Chat E2E Local");
      await page.getByTestId("ai-model-endpoint-uri-input").fill(mockLlm.baseUrl);
      await page.getByTestId("save-and-test-ai-model-btn").click();
      await expect(page.getByTestId("ai-model-display-name-input")).toBeHidden({ timeout: 15000 });

      await page.getByTestId("open-create-ai-model-modal-btn").click();
      await page.getByTestId("llm-provider-preset-ollama").click();
      await page.getByTestId("ai-model-usage-embedding-btn").click();
      await page.getByTestId("ai-model-display-name-input").fill("Embedding 1024 E2E");
      await page.getByTestId("ai-model-primary-model-input").fill("bge-m3:latest");
      await page.getByTestId("ai-model-endpoint-uri-input").fill(mockLlm.baseUrl);
      await page.getByTestId("ai-model-auth-mode-select").selectOption("none_local");
      await page.getByTestId("save-and-test-ai-model-btn").click();
      await expect(page.getByTestId("ai-model-display-name-input")).toBeHidden({ timeout: 15000 });

      await page.getByTestId("relaunch-reindex-button").click();
      await expect(page.getByTestId("reindex-feedback")).toBeVisible({ timeout: 15000 });

      await page.goto("/assistant");
      await expect(page.getByTestId("assistant-no-embedding-banner")).toBeHidden({ timeout: 15000 });

      await page.evaluate(() => {
        window.localStorage.clear();
        window.sessionStorage.clear();
      });
      await page.goto("/settings?tab=models");
      await page.reload();
      await expect(page.getByTestId("ai-models-master-table")).toContainText("Chat E2E Local", {
        timeout: 20000,
      });
      await expect(page.getByTestId("ai-models-master-table")).toContainText("Embedding 1024 E2E");

      expectDbRowExists(
        "SELECT id, usage, display_name, endpoint_uri, is_active FROM workspace_llm_tier_mappings WHERE display_name = :name AND usage = 'chat' AND is_active = TRUE",
        { name: "Chat E2E Local" },
        "modèle Chat persisté dans workspace_llm_tier_mappings",
      );
      expectDbRowExists(
        "SELECT id, usage, display_name, endpoint_uri, is_active FROM workspace_llm_tier_mappings WHERE display_name = :name AND usage = 'embedding' AND is_active = TRUE",
        { name: "Embedding 1024 E2E" },
        "modèle Embedding 1024 persisté dans workspace_llm_tier_mappings",
      );
      expectDbRowExists(
        "SELECT id, target_model_name, status FROM rag_reindexing_jobs WHERE target_model_name = :model",
        { model: "bge-m3:latest" },
        "job de réindexation persisté dans rag_reindexing_jobs",
      );
    } finally {
      await mockLlm.close();
    }
  });

  test("connecteur socle (secret write-only) et jeton Passthrough personnel persistent après F5", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    await openSettingsTabViaUi(page, "connectors");
    await expect(page.getByTestId("settings-connectors-section")).toBeVisible({ timeout: 15000 });

    const adminSecretPlaceholder = "e2e-connector-secret-placeholder"; // pragma: allowlist secret
    await page.getByTestId("connector-kind-select").selectOption("GITLAB");
    await page.getByTestId("connector-name-input").fill("GitLab Entreprise E2E");
    await page.getByTestId("connector-base-url-input").fill("https://gitlab.e2e.internal");
    await page.getByTestId("connector-auth-mode-select").selectOption("OAUTH2_PASSTHROUGH");
    await page.getByTestId("connector-admin-secret-input").fill(adminSecretPlaceholder);
    await page.getByTestId("register-connector-submit-btn").click();

    const connectorRow = page.locator("[data-testid^='enterprise-connector-row-']").first();
    await expect(connectorRow).toBeVisible({ timeout: 15000 });
    const rowTestId = (await connectorRow.getAttribute("data-testid")) ?? "";
    const connectorId = rowTestId.replace("enterprise-connector-row-", "");
    await expect(page.getByTestId(`connector-secret-badge-${connectorId}`)).toBeVisible();
    await expect(page.getByTestId("settings-connectors-section")).not.toContainText(
      adminSecretPlaceholder,
    );

    const passthroughSecretPlaceholder = "e2e-passthrough-credential-value"; // pragma: allowlist secret
    await openUserSettingsTab(page, "PASSTHROUGH_SOURCES");
    await expect(page.getByTestId(`user-passthrough-card-${connectorId}`)).toBeVisible({
      timeout: 15000,
    });
    await page.getByTestId(`passthrough-configure-btn-${connectorId}`).click();
    await page.getByTestId(`passthrough-login-input-${connectorId}`).fill("alice.gitlab");
    await page
      .getByTestId(`passthrough-token-input-${connectorId}`)
      .fill(passthroughSecretPlaceholder);
    await page.getByTestId(`passthrough-save-btn-${connectorId}`).click();
    await expect(page.getByTestId(`passthrough-connected-badge-${connectorId}`)).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByTestId("user-settings-panel-PASSTHROUGH_SOURCES")).not.toContainText(
      passthroughSecretPlaceholder,
    );

    await page.evaluate(() => {
      window.localStorage.clear();
      window.sessionStorage.clear();
    });
    await page.reload();
    await openUserSettingsTab(page, "PASSTHROUGH_SOURCES");
    await expect(page.getByTestId(`passthrough-connected-badge-${connectorId}`)).toBeVisible({
      timeout: 15000,
    });

    expectDbRowExists(
      "SELECT id, connector_kind, name, base_url FROM enterprise_connectors WHERE name = :name",
      { name: "GitLab Entreprise E2E" },
      "connecteur socle persisté dans enterprise_connectors",
    );
    expectDbRowExists(
      "SELECT id, external_author_login, status FROM user_connector_passthrough_tokens WHERE external_author_login = :login AND status = 'ACTIVE'",
      { login: "alice.gitlab" },
      "jeton passthrough persisté dans user_connector_passthrough_tokens",
    );
  });

  test("interception Permission Broker affiche la carte de procédure et persiste permission_broker_tickets", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    const adminToken = await getBearerTokenFromSession(page);
    const restrictedUri = "git://gitlab.internal/platform/infra-core";

    const brokerRes = await page.request.post("/api/v1/permissions/broker/check-access", {
      headers: { Authorization: `Bearer ${adminToken}` },
      data: {
        target_uri: restrictedUri,
        execution_identity: "passthrough",
        step_key: "fetch_repo",
        step_number: 1,
        simulated_upstream_status: 403,
        raise_on_denied: false,
      },
    });
    expect(brokerRes.status()).toBe(200);
    const brokerPayload = (await brokerRes.json()) as {
      status: string;
      ticket?: { request_url?: string } | null;
    };
    expect(brokerPayload.status).toBe("WAITING_FOR_PERMISSION");
    expect(brokerPayload.ticket?.request_url).toBeTruthy();

    await page.goto("/assistant");
    await expect(page.getByTestId("permission-broker-card")).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("permission-broker-card-procedure")).toBeVisible();
    await expect(page.getByTestId("permission-broker-jira-link")).toBeVisible();

    expectDbRowExists(
      "SELECT id, target_uri, request_url, status FROM permission_broker_tickets WHERE target_uri = :target_uri",
      { target_uri: restrictedUri },
      "ticket Permission Broker persisté dans permission_broker_tickets",
    );
  });
});
