import fs from "node:fs";
import path from "node:path";

interface OpenApiSchema {
  $ref?: string;
  type?: string;
  format?: string;
  enum?: unknown[];
  const?: unknown;
  required?: string[];
  properties?: Record<string, OpenApiSchema>;
  additionalProperties?: boolean | OpenApiSchema;
  items?: OpenApiSchema;
  anyOf?: OpenApiSchema[];
  oneOf?: OpenApiSchema[];
  allOf?: OpenApiSchema[];
}

interface OpenApiParameter {
  name: string;
  in: "path" | "query" | "header" | "cookie";
  required?: boolean;
  schema?: OpenApiSchema;
}

interface OpenApiOperation {
  parameters?: OpenApiParameter[];
  requestBody?: {
    required?: boolean;
    content?: Record<string, { schema?: OpenApiSchema }>;
  };
}

interface OpenApiSpec {
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

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function loadOpenApiSpec(): OpenApiSpec {
  const specPath = path.resolve(
    __dirname,
    "../../../../../packages/api-client/openapi.json",
  );
  return JSON.parse(fs.readFileSync(specPath, "utf-8")) as OpenApiSpec;
}

const SPEC = loadOpenApiSpec();
const SCHEMAS: Record<string, OpenApiSchema> = SPEC.components?.schemas ?? {};

function compilePathEntries(): CompiledPathEntry[] {
  const entries: CompiledPathEntry[] = [];
  for (const [template, pathItem] of Object.entries(SPEC.paths ?? {})) {
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

const COMPILED_PATHS = compilePathEntries();

function resolveSchema(schema: OpenApiSchema): OpenApiSchema {
  if (!schema.$ref) return schema;
  const refName = schema.$ref.split("/").pop() ?? "";
  return SCHEMAS[refName] ?? schema;
}

function schemaAcceptsType(rawSchema: OpenApiSchema, targetType: string): boolean {
  const schema = resolveSchema(rawSchema);
  if (schema.type === targetType) return true;
  const union = schema.anyOf ?? schema.oneOf ?? [];
  return union.some((sub) => schemaAcceptsType(sub, targetType));
}

function formatError(ctx: string, message: string): Error {
  return new Error(`[vitestFetchTransport FAIL-CLOSED OpenAPI] ${ctx} : ${message}`);
}

function checkValueMatchesSchema(
  rawSchema: OpenApiSchema,
  value: unknown,
  ctx: string,
  method: string,
): string | null {
  const schema = resolveSchema(rawSchema);

  if (schema.allOf && schema.allOf.length > 0) {
    for (const sub of schema.allOf) {
      const err = checkValueMatchesSchema(sub, value, ctx, method);
      if (err) return err;
    }
    return null;
  }

  const unionBranches = schema.anyOf ?? schema.oneOf;
  if (unionBranches && unionBranches.length > 0) {
    const branchErrors: string[] = [];
    for (const branch of unionBranches) {
      const err = checkValueMatchesSchema(branch, value, ctx, method);
      if (!err) return null;
      branchErrors.push(err);
    }
    return `aucune branche anyOf/oneOf satisfaite (${branchErrors[0] ?? "type invalide"})`;
  }

  if (schema.const !== undefined && value !== schema.const) {
    return `valeur attendue ${JSON.stringify(schema.const)}, reçu ${JSON.stringify(value)}`;
  }

  if (schema.enum && !schema.enum.includes(value)) {
    return `valeur ${JSON.stringify(value)} hors enum [${schema.enum.join(", ")}]`;
  }

  const expectedType = schema.type;
  if (expectedType === "null") {
    return value === null ? null : `null attendu, reçu ${typeof value}`;
  }
  if (expectedType === "string") {
    if (typeof value !== "string") return `string attendu, reçu ${typeof value}`;
    if (schema.format === "uuid" && !UUID_REGEX.test(value)) {
      return `UUID invalide (${JSON.stringify(value)}) sur champ format: "uuid"`;
    }
    return null;
  }
  if (expectedType === "integer") {
    if (typeof value !== "number" || !Number.isInteger(value)) {
      return `integer attendu, reçu ${JSON.stringify(value)}`;
    }
    return null;
  }
  if (expectedType === "number") {
    if (typeof value !== "number" || Number.isNaN(value)) {
      return `number attendu, reçu ${JSON.stringify(value)}`;
    }
    return null;
  }
  if (expectedType === "boolean") {
    if (typeof value !== "boolean") return `boolean attendu, reçu ${typeof value}`;
    return null;
  }
  if (expectedType === "array") {
    if (!Array.isArray(value)) return `array attendu, reçu ${typeof value}`;
    if (schema.items) {
      for (let i = 0; i < value.length; i += 1) {
        const err = checkValueMatchesSchema(schema.items, value[i], `${ctx}[${i}]`, method);
        if (err) return err;
      }
    }
    return null;
  }
  if (expectedType === "object" || schema.properties) {
    if (typeof value !== "object" || value === null || Array.isArray(value)) {
      return `object attendu, reçu ${Array.isArray(value) ? "array" : typeof value}`;
    }
    const obj = value as Record<string, unknown>;
    const props = schema.properties ?? {};
    for (const reqKey of schema.required ?? []) {
      if (!(reqKey in obj) || obj[reqKey] === undefined) {
        return `champ obligatoire '${reqKey}' manquant dans ${ctx}`;
      }
    }
    const forbidExtra =
      schema.additionalProperties === false ||
      (schema.additionalProperties === undefined &&
        Object.keys(props).length > 0 &&
        ["POST", "PUT", "PATCH"].includes(method));
    for (const [key, propVal] of Object.entries(obj)) {
      if (propVal === undefined) continue;
      const propSchema = props[key];
      if (propSchema) {
        const err = checkValueMatchesSchema(propSchema, propVal, `${ctx}.${key}`, method);
        if (err) return `${key}: ${err}`;
      } else if (forbidExtra) {
        return `champ non déclaré '${key}' interdit (additionalProperties: false) dans ${ctx}`;
      } else if (typeof schema.additionalProperties === "object") {
        const err = checkValueMatchesSchema(
          schema.additionalProperties,
          propVal,
          `${ctx}.${key}`,
          method,
        );
        if (err) return `${key}: ${err}`;
      }
    }
    return null;
  }

  return null;
}

export function validateRequestAgainstOpenApi(params: {
  method: string;
  parsedUrl: URL;
  body: unknown;
  hasRawBody: boolean;
  isMultipart: boolean;
}): void {
  const { method, parsedUrl, body, hasRawBody, isMultipart } = params;
  const pathname = parsedUrl.pathname;
  const lowerMethod = method.toLowerCase();

  let matchedEntry: CompiledPathEntry | null = null;
  let pathValues: Record<string, string> = {};
  for (const entry of COMPILED_PATHS) {
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
        if (schemaAcceptsType(param.schema, "boolean")) {
          if (rawVal === "true") typedVal = true;
          else if (rawVal === "false") typedVal = false;
        } else if (
          schemaAcceptsType(param.schema, "integer") ||
          schemaAcceptsType(param.schema, "number")
        ) {
          const parsed = Number(rawVal);
          if (!Number.isNaN(parsed) && rawVal.trim() !== "") typedVal = parsed;
        }
        const err = checkValueMatchesSchema(
          param.schema,
          typedVal,
          `query.${param.name}`,
          method,
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
      const err = checkValueMatchesSchema(jsonContent.schema, body, "body", method);
      if (err) throw formatError(`${method} ${pathname}`, err);
    }
  }
}
