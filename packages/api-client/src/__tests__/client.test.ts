import { describe, expect, it, vi } from "vitest";
import { createOrciaApiClient, OrciaProblemError } from "../index";

describe("createOrciaApiClient", () => {
  it("fetches /api/v1/health with Accept-Language and X-Trace-Id headers", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "ok",
        version: "0.1.0",
        trace_id: "0192c4e0000070008000000000000001",
      }),
    });

    const client = createOrciaApiClient({
      baseUrl: "http://localhost:8000",
      locale: "fr",
      traceId: "0192c4e0000070008000000000000001",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    const res = await client.getHealth();
    expect(res.status).toBe("ok");
    expect(mockFetch).toHaveBeenCalledWith("http://localhost:8000/api/v1/health", {
      method: "GET",
      headers: {
        Accept: "application/json, application/problem+json",
        "Accept-Language": "fr",
        "X-Trace-Id": "0192c4e0000070008000000000000001",
      },
    });
  });

  it("throws OrciaProblemError when backend returns RFC 9457 ProblemDetails", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({
        type: "https://orcia.io/problems/observer-mode-read-only",
        title: "Mode observateur en lecture seule",
        status: 403,
        detail: "Cette action de modification est interdite en mode READ_ONLY_OBSERVER.",
        instance: "/api/v1/navigation/shell",
        error_code: "ERR_OBSERVER_MODE_READ_ONLY",
        trace_id: "0192c4e0000070008000000000000002",
      }),
    });

    const client = createOrciaApiClient({
      baseUrl: "http://localhost:8000",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    await expect(client.getShellNavigation("scope-global")).rejects.toBeInstanceOf(
      OrciaProblemError,
    );
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/navigation/shell?scope_id=scope-global",
      {
        method: "GET",
        headers: {
          Accept: "application/json, application/problem+json",
          "Accept-Language": "fr",
        },
      },
    );
  });

  it("fetches /api/v1/navigation/shell on 200 OK without query string when scopeId is omitted", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        active_scope_id: "scope-ws-orcia",
        scopes: [],
        modules: [],
        human_profile: {
          archetype_key: "TECH_LEAD",
          displayName: "Tech Lead",
          access_mode: "CONTRIBUTOR_ACTION_REQUIRED",
        },
        trace_id: "0192c4e0000070008000000000000003",
      }),
    });

    const client = createOrciaApiClient({
      baseUrl: "http://localhost:8000",
      locale: "en",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    const res = await client.getShellNavigation();
    expect(res.active_scope_id).toBe("scope-ws-orcia");
    expect(mockFetch).toHaveBeenCalledWith("http://localhost:8000/api/v1/navigation/shell", {
      method: "GET",
      headers: {
        Accept: "application/json, application/problem+json",
        "Accept-Language": "en",
      },
    });
  });

  it("synthesizes a fallback ProblemDetails when a non-2xx response has a non-JSON body", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
      headers: {
        get: (name: string) =>
          name.toLowerCase() === "x-trace-id" ? "0192c4e0000070008000000000000099" : null,
      },
      json: async () => {
        throw new SyntaxError("Unexpected token < in JSON at position 0");
      },
    });

    const client = createOrciaApiClient({
      baseUrl: "http://localhost:8000",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    try {
      await client.getHealth();
      expect.unreachable("Should have thrown OrciaProblemError");
    } catch (err) {
      expect(err).toBeInstanceOf(OrciaProblemError);
      const problemErr = err as OrciaProblemError;
      expect(problemErr.problem.status).toBe(502);
      expect(problemErr.problem.error_code).toBe("ERR_INTERNAL_SERVER_ERROR");
      expect(problemErr.problem.instance).toBe("/api/v1/health");
      expect(problemErr.problem.trace_id).toBe("0192c4e0000070008000000000000099");
    }
  });

  it("supports Story 1.2 & Story 1.3 auth, workspaces, federated catalog, CAS, 4-layer merge, and BMAD endpoints", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ok" }),
    });

    const client = createOrciaApiClient({
      baseUrl: "http://localhost:8000",
      accessToken: "jwt-token-123",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    await client.loginLocal({ email: "marc.lead@orcia.io", password: "secret" });
    await client.loginOidc({ oidc_subject: "oidc|marc-lead" });
    await client.refreshSession();
    await client.logoutSession();
    await client.getMe("marc");
    await client.listWorkspaces("claire");
    await client.checkWorkspaceMutation("ws-1", "marc");
    await client.inspectCatalogResource("res-1", "marc");
    await client.getCatalogResourceSource("res-1", "marc");
    await client.storePassthroughCredential(
      {
        connector_scheme: "git",
        target_host: "gitlab.entreprise.io",
        plaintext_secret: "pat-123",
      },
      "marc",
    );
    await client.listCatalogItems("marc");
    await client.promoteCatalogItem(
      "res-jira-secops-playbook",
      { target_scope: "SHARED_WORKSPACE" },
      "marc",
    );
    await client.resolveFederatedUri(
      { uri: "git://gitlab.entreprise.io/payments/checkout-web" },
      "marc",
    );
    await client.getCasObject(
      "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "marc",
    );
    await client.resolveEffectiveWorkflow(
      {
        workflow_uri: "db://orcia/catalog/payment-delivery-workflow@v1.2.0",
        workspace_id: "ws-solution-paiement",
      },
      "marc",
    );
    await client.importBmadSkillPack(
      {
        uri: "git://gitlab.entreprise.io/payments/checkout-web/skills/bmad-pack@v1.0.0",
        skill_markdown: "---\nname: checkout-pack\ndescription: Pack Checkout\n---\n# Body",
        customize_toml: "",
        steps: [{ filename: "step-01.md", content_markdown: "# Step 1" }],
      },
      "marc",
    );
    await client.getPermissionBrokerState("marc", "ws-solution-paiement");
    const kbMarkdown =
      "---\nuri_pattern: git://github.enterprise/payments/*\nrequired_role: ROLE_GIT_PAYMENTS_CORE\napprover_team: IAM-Payments-Squad\nrequest_url_template: https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa?pid=10420\nsla_hours: 4\n---\n# Guide";
    await client.importPermissionPolicyMarkdown(
      {
        markdown_text: kbMarkdown,
      },
      "marc",
    );
    await client.checkConnectorAccess(
      {
        target_uri: "git://github.enterprise/payments/checkout-core.git",
        execution_identity: "passthrough",
        raise_on_denied: false,
      },
      "nadia",
    );
    await client.applyPermissionTicketAction("IAM-4821", { action: "REPLAY" }, "nadia");
    await client.getSystemBootstrapState("karim");
    await client.executeInitOrganization(
      {
        organization_name: "Entreprise ORCIA Group",
        oidc_enabled: true,
        local_argon2id_enabled: true,
        rbac_role_mappings: { PLATFORM_ADMIN: "grp-admin" },
        llm_endpoints: [
          {
            id: "ep-1",
            endpoint_key: "claude",
            provider_slug: "anthropic",
            model_family: "anthropic-claude",
            model_name: "claude-3-7-sonnet",
            endpoint_uri: "https://llm.orcia.internal/v1/anthropic",
          },
          {
            id: "ep-2",
            endpoint_key: "mistral",
            provider_slug: "mistral",
            model_family: "mistral-large",
            model_name: "mistral-large-2411",
            endpoint_uri: "https://llm.orcia.internal/v1/mistral",
          },
        ],
      },
      "karim",
    );
    await client.executeInitWorkspace(
      {
        team_slug: "team-fraud",
        team_name: "Équipe Fraude",
        parent_org_unit_id: "0192c4e0-0000-7000-8000-000000000102",
        workspaces: [{ slug: "ws-fraud-core", name: "Workspace Fraude Core" }],
      },
      "marc",
    );
    await client.executeInitDatasource(
      {
        workspace_id: "0192c4e0-0000-7000-8000-000000000201",
        alias: "git-checkout-bff",
        scheme: "git",
        uri: "git://gitlab.entreprise.io/payments/checkout-bff",
        role: "code_backend",
        freshness_ttl_days: 90,
        permission_broker_markdown: kbMarkdown,
        human_anchor_justification:
          "Validation architecturale et sécurité du périmètre Git BFF par le Tech Lead.",
        human_anchor_signature: "Marc (Tech Lead Checkout)",
      },
      "marc",
    );
    await client.executeInitUser(
      {
        confirmed_human_profile_archetype: "DEVELOPER",
        passthrough_secrets: [
          {
            connector_scheme: "git",
            target_host: "gitlab.entreprise.io",
            plaintext_secret: "glpat-secret-token",
          },
        ],
      },
      "nadia",
    );

    expect(mockFetch).toHaveBeenCalledTimes(25);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/bootstrap/state?persona_key=karim",
      expect.objectContaining({ method: "GET" }),
    );
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/bootstrap/init-datasource?persona_key=marc",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("supports Epic 2 (Stories 2.1-2.4) ontology & hybrid RAG SDK methods", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ok" }),
    });

    const client = createOrciaApiClient({
      baseUrl: "http://localhost:8000",
      accessToken: "jwt-token-123",
      fetchImpl: mockFetch as unknown as typeof fetch,
    });

    await client.getOntologyAndRagState(true);
    await client.resolveOntologyHierarchy(
      {
        enterprise_scope_id: "scope-global",
        domain_scope_id: "scope-bu-digital",
        team_chain_scope_ids: ["scope-team-architecture", "scope-subteam-checkout"],
        workspace_scope_id: "ws-solution-paiement",
        run_scope_id: "run-checkout-001",
      },
      true,
    );
    await client.upsertOntologyConcept(
      {
        concept_key: "concept-l4-test",
        canonical_term: "TestTerm",
        level: "4_RUN_EPHEMERAL",
        scope_id: "run-checkout-001",
        definition_text: "Définition test",
      },
      true,
    );
    await client.simulateOntologyWhatIf(
      {
        concept_key: "concept-l3-ws-idempotency-key",
        proposed_change: "Nouveau jeton UUIDv7",
      },
      true,
    );
    await client.promoteOntologyProposal(
      {
        proposal_key: "prop-concept-l4-3ds-frictionless-exemption-to-3_workspace",
      },
      true,
    );
    await client.searchHybridRag(
      {
        workspace_id: "ws-solution-paiement",
        query_text: "seuil validation",
        allowed_datasource_aliases: ["confluence-claims"],
        top_k: 5,
      },
      true,
    );
    await client.indexDbDdlSchema(
      {
        workspace_id: "ws-solution-paiement",
        datasource_id: "ds-db-1",
        datasource_alias: "db-claims-schema",
        db_uri: "db://postgres.internal/claims_prod",
        ddl_sql: "CREATE TABLE claims (id UUID PRIMARY KEY);",
        schema_version: "2026.10.1",
      },
      true,
    );
    await client.auditDocVsCode(
      {
        confluence_uri: "confluence://CLAIMS/pages/101-spec-seuil-validation",
        git_repo_uri: "git://claims/core-engine",
        git_symbol: "calculate_reserve",
        doc_rule_summary: "5000 EUR",
        code_rule_summary: "7500 EUR",
        newer_done_jira_key: "PAY-142",
      },
      true,
    );

    expect(mockFetch).toHaveBeenCalledTimes(8);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/ontology-rag/state?fixture=true",
      expect.objectContaining({ method: "GET" }),
    );
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/ontology-rag/tripartite/audit-doc-vs-code?fixture=true",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
