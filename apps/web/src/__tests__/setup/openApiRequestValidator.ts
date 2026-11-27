import fs from "node:fs";
import path from "node:path";
import {
  checkValueMatchesSchema,
  schemaAcceptsType,
  type OpenApiSchema,
} from "./openApiSchemaChecker";

interface OpenApiParameter {
  name: string;
  in: "path" | "query" | "header" | "cookie";
  required?: boolean;
  schema?: OpenApiSchema;
}

interface OpenApiOperation {
  security?: Array<Record<string, string[]>>;
  parameters?: OpenApiParameter[];
  requestBody?: {
    required?: boolean;
    content?: Record<string, { schema?: OpenApiSchema }>;
  };
}

interface OpenApiSpec {
  security?: Array<Record<string, string[]>>;
  paths: Record<string, Record<string, unknown>>;
  components?: { schemas?: Record<string, OpenApiSchema> };
}

interface CompiledPathEntry {
  template: string;
  regex: RegExp;
  paramNames: string[];
  staticSegments: number;
  pathItem: Record<string, unknown>;
}

const VALIDATOR_CACHE_KEY = Symbol.for("orcia.vitest.openApiValidatorCache");

interface OpenApiValidatorCache {
  mtimeMs: number;
  spec: OpenApiSpec;
  schemas: Record<string, OpenApiSchema>;
  compiledPaths: CompiledPathEntry[];
}

function compilePathEntries(spec: OpenApiSpec): CompiledPathEntry[] {
  const entries: CompiledPathEntry[] = [];
  for (const [template, pathItem] of Object.entries(spec.paths ?? {})) {
    const paramNames: string[] = [];
    const segments = template.split("/");
    let staticSegments = 0;
    const regexParts = segments.map((seg) => {
      const m = /^\{([^}]+)\}$/.exec(seg);
      if (m && m[1]) {
        paramNames.push(m[1]);
        return "([^/]+)";
      }
      if (seg.length > 0) staticSegments += 1;
      return seg.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    });
    entries.push({
      template,
      regex: new RegExp(`^${regexParts.join("/")}$`),
      paramNames,
      staticSegments,
      pathItem,
    });
  }
  entries.sort((a, b) => {
    if (a.paramNames.length !== b.paramNames.length) {
      return a.paramNames.length - b.paramNames.length;
    }
    return b.staticSegments - a.staticSegments;
  });
  return entries;
}

function getOpenApiCache(): OpenApiValidatorCache {
  const specPath = path.resolve(
    __dirname,
    "../../../../../packages/api-client/openapi.json",
  );
  const mtimeMs = fs.statSync(specPath).mtimeMs;
  const globalStore = globalThis as Record<symbol, OpenApiValidatorCache | undefined>;
  const existing = globalStore[VALIDATOR_CACHE_KEY];
  if (existing && existing.mtimeMs === mtimeMs) {
    return existing;
  }
  const spec = JSON.parse(fs.readFileSync(specPath, "utf-8")) as OpenApiSpec;
  const cache: OpenApiValidatorCache = {
    mtimeMs,
    spec,
    schemas: spec.components?.schemas ?? {},
    compiledPaths: compilePathEntries(spec),
  };
  globalStore[VALIDATOR_CACHE_KEY] = cache;
  return cache;
}

function formatError(ctx: string, message: string): Error {
  return new Error(`[vitestFetchTransport FAIL-CLOSED OpenAPI] ${ctx} : ${message}`);
}

export function validateRequestAgainstOpenApi(params: {
  method: string;
  parsedUrl: URL;
  body: unknown;
  hasRawBody: boolean;
  isMultipart: boolean;
  headers?: Headers;
}): Response | null {
  const { spec, schemas, compiledPaths } = getOpenApiCache();
  const { method, parsedUrl, body, hasRawBody, isMultipart } = params;
  const pathname = parsedUrl.pathname;
  const lowerMethod = method.toLowerCase();

  let matchedEntry: CompiledPathEntry | null = null;
  let pathValues: Record<string, string> = {};
  for (const entry of compiledPaths) {
    const m = entry.regex.exec(pathname);
    if (m) {
      matchedEntry = entry;
      entry.paramNames.forEach((name, idx) => {
        pathValues[name] = decodeURIComponent(m[idx + 1] ?? "");
      });
      break;
    }
  }

  if (!matchedEntry) {
    throw formatError(`${method} ${pathname}`, "route absente de packages/api-client/openapi.json");
  }

  const op = matchedEntry.pathItem[lowerMethod] as OpenApiOperation | undefined;
  if (!op) {
    throw formatError(
      `${method} ${pathname}`,
      `méthode ${method} non déclarée sur ${matchedEntry.template}`,
    );
  }

  const pathLevelParams = (matchedEntry.pathItem.parameters as OpenApiParameter[] | undefined) ?? [];
  const allParams = [...pathLevelParams, ...(op.parameters ?? [])];
  for (const param of allParams) {
    if (param.in === "path") {
      const val = pathValues[param.name];
      if (val === undefined || val === "") {
        throw formatError(`${method} ${pathname}`, `paramètre path '${param.name}' manquant`);
      }
      if (param.schema) {
        const err = checkValueMatchesSchema(
          param.schema,
          val,
          `path.${param.name}`,
          method,
          schemas,
        );
        if (err) throw formatError(`${method} ${pathname}`, `path.${param.name}: ${err}`);
      }
    } else if (param.in === "query") {
      const hasQuery = parsedUrl.searchParams.has(param.name);
      const rawVal = parsedUrl.searchParams.get(param.name);
      if (param.required && (!hasQuery || rawVal === null)) {
        throw formatError(
          `${method} ${pathname}`,
          `paramètre query obligatoire '${param.name}' manquant`,
        );
      }
      if (hasQuery && rawVal !== null && param.schema) {
        let typedVal: unknown = rawVal;
        if (schemaAcceptsType(param.schema, "boolean", schemas)) {
          if (rawVal === "true") typedVal = true;
          else if (rawVal === "false") typedVal = false;
        } else if (
          schemaAcceptsType(param.schema, "integer", schemas) ||
          schemaAcceptsType(param.schema, "number", schemas)
        ) {
          const parsed = Number(rawVal);
          if (!Number.isNaN(parsed) && rawVal.trim() !== "") typedVal = parsed;
        }
        const err = checkValueMatchesSchema(
          param.schema,
          typedVal,
          `query.${param.name}`,
          method,
          schemas,
        );
        if (err) throw formatError(`${method} ${pathname}`, `query.${param.name}: ${err}`);
      }
    }
  }

  if (op.requestBody && !isMultipart) {
    const jsonContent = op.requestBody.content?.["application/json"];
    if (op.requestBody.required && !hasRawBody) {
      throw formatError(`${method} ${pathname}`, "corps JSON requestBody obligatoire manquant");
    }
    if (jsonContent?.schema && hasRawBody) {
      const err = checkValueMatchesSchema(jsonContent.schema, body, "body", method, schemas);
      if (err) throw formatError(`${method} ${pathname}`, err);
    }
  }

  const effectiveSecurity = op.security ?? spec.security ?? [];
  if (Array.isArray(effectiveSecurity) && effectiveSecurity.length > 0) {
    const rawAuth = params.headers?.get("Authorization") ?? "";
    const bearerMatch = /^Bearer\s+(\S+)$/i.exec(rawAuth.trim());
    if (!bearerMatch?.[1]) {
      return new Response(
        JSON.stringify({
          type: "https://orcia.ia/errors/ERR_AUTH_REQUIRED",
          title: "Authentification requise",
          status: 401,
          detail: `Jeton Bearer requis pour ${method} ${pathname}.`,
          instance: pathname,
          error_code: "ERR_AUTH_REQUIRED",
          trace_id: "00000000000000000000000000000000",
        }),
        { status: 401, headers: { "Content-Type": "application/problem+json" } },
      );
    }
  }

  return null;
}
