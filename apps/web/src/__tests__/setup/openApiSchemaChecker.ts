export interface OpenApiSchema {
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

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function resolveSchema(
  schema: OpenApiSchema,
  schemas: Record<string, OpenApiSchema>,
): OpenApiSchema {
  if (!schema.$ref) return schema;
  const refName = schema.$ref.split("/").pop() ?? "";
  return schemas[refName] ?? schema;
}

export function schemaAcceptsType(
  rawSchema: OpenApiSchema,
  targetType: string,
  schemas: Record<string, OpenApiSchema>,
): boolean {
  const schema = resolveSchema(rawSchema, schemas);
  if (schema.type === targetType) return true;
  const union = schema.anyOf ?? schema.oneOf ?? [];
  return union.some((sub) => schemaAcceptsType(sub, targetType, schemas));
}

export function checkValueMatchesSchema(
  rawSchema: OpenApiSchema,
  value: unknown,
  ctx: string,
  method: string,
  schemas: Record<string, OpenApiSchema>,
): string | null {
  const schema = resolveSchema(rawSchema, schemas);

  if (schema.allOf && schema.allOf.length > 0) {
    for (const sub of schema.allOf) {
      const err = checkValueMatchesSchema(sub, value, ctx, method, schemas);
      if (err) return err;
    }
    return null;
  }

  const unionBranches = schema.anyOf ?? schema.oneOf;
  if (unionBranches && unionBranches.length > 0) {
    const branchErrors: string[] = [];
    for (const branch of unionBranches) {
      const err = checkValueMatchesSchema(branch, value, ctx, method, schemas);
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
        const err = checkValueMatchesSchema(
          schema.items,
          value[i],
          `${ctx}[${i}]`,
          method,
          schemas,
        );
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
        const err = checkValueMatchesSchema(propSchema, propVal, `${ctx}.${key}`, method, schemas);
        if (err) return `${key}: ${err}`;
      } else if (forbidExtra) {
        return `champ non déclaré '${key}' interdit (additionalProperties: false) dans ${ctx}`;
      } else if (typeof schema.additionalProperties === "object") {
        const err = checkValueMatchesSchema(
          schema.additionalProperties,
          propVal,
          `${ctx}.${key}`,
          method,
          schemas,
        );
        if (err) return `${key}: ${err}`;
      }
    }
    return null;
  }

  return null;
}
