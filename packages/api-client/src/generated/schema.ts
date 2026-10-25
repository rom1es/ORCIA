/**
 * AUTO-GENERATED FILE FROM FASTAPI OPENAPI 3.1 SCHEMA — DO NOT EDIT MANUALLY.
 * Regenerate via: `.venv/bin/python scripts/export_openapi.py`
 */

export interface components {
  schemas: {
    HealthResponse: {
      status?: "ok";
      trace_id: string;
      version: string;
    };
    HumanProfileBadge: {
      access_mode: "CONTRIBUTOR_ACTION_REQUIRED" | "READ_ONLY_OBSERVER";
      archetype_key: string;
      display_name: string;
    };
    ProblemDetails: {
      detail: string;
      error_code: string;
      instance?: string | null;
      permission_broker_hint?: string | null;
      status: number;
      title: string;
      trace_id: string;
      type?: string;
    };
    ScopeNode: {
      access_mode?: "CONTRIBUTOR_ACTION_REQUIRED" | "READ_ONLY_OBSERVER";
      id: string;
      level: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
      name: string;
      parent_id?: string | null;
    };
    ShellModuleItem: {
      contributor_badge_count?: number;
      enabled?: boolean;
      has_stale_warning?: boolean;
      icon: string;
      key: "cockpit" | "inbox" | "catalog" | "ontology" | "gates" | "finops" | "admin";
      order: number;
      route: string;
    };
    ShellNavigationResponse: {
      active_scope_id: string;
      human_profile: components["schemas"]["HumanProfileBadge"];
      modules: (components["schemas"]["ShellModuleItem"])[];
      scopes: (components["schemas"]["ScopeNode"])[];
      trace_id: string;
    };
  };
}

export interface paths {
  "/api/v1/health": {
    get: {
      responses: {
        200: components["schemas"]["HealthResponse"];
      };
    };
  };
  "/api/v1/navigation/shell": {
    get: {
      responses: {
        200: components["schemas"]["ShellNavigationResponse"];
      };
    };
  };
}

export type ProblemDetails = components["schemas"]["ProblemDetails"];
export type HealthResponse = components["schemas"]["HealthResponse"];
export type ShellModuleItem = components["schemas"]["ShellModuleItem"];
export type ScopeNode = components["schemas"]["ScopeNode"];
export type HumanProfileBadge = components["schemas"]["HumanProfileBadge"];
export type ShellNavigationResponse = components["schemas"]["ShellNavigationResponse"];
