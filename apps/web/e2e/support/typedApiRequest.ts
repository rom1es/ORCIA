import { expect, type APIRequestContext, type APIResponse, type Page } from "@playwright/test";
import type { components, paths } from "@orcia/api-client";

export type ApiSchemaComponents = components["schemas"];
export type ApiPaths = paths;

type HttpMethod = "get" | "post" | "put" | "patch" | "delete";

type PathsWithMethod<M extends HttpMethod> = {
  [P in keyof paths]: M extends keyof paths[P] ? P : never;
}[keyof paths];

type ReplacePathParams<S extends string> = S extends `${infer Head}{${string}}${infer Tail}`
  ? `${Head}${string}${ReplacePathParams<Tail>}`
  : S;

export type EndpointPath<M extends HttpMethod> =
  | ReplacePathParams<Extract<PathsWithMethod<M>, string>>
  | `${ReplacePathParams<Extract<PathsWithMethod<M>, string>>}?${string}`;

export type RequestTarget = Page | APIRequestContext;

export interface TypedRequestOptions<TBody = unknown> {
  readonly headers?: Record<string, string>;
  readonly data?: TBody;
  readonly token?: string;
  readonly timeout?: number;
}

export interface TypedApiResponse<TRes = unknown> {
  readonly raw: APIResponse;
  status(): number;
  ok(): boolean;
  headers(): Record<string, string>;
  text(): Promise<string>;
  json(): Promise<TRes>;
}

function resolveRequestContext(target: RequestTarget): APIRequestContext {
  return "request" in target ? target.request : target;
}

function buildHeaders<TBody>(options?: TypedRequestOptions<TBody>): Record<string, string> | undefined {
  const merged: Record<string, string> = { ...(options?.headers ?? {}) };
  if (options?.token && !merged.Authorization && !merged.authorization) {
    merged.Authorization = `Bearer ${options.token}`;
  }
  return Object.keys(merged).length > 0 ? merged : undefined;
}

function wrapResponse<TRes>(res: APIResponse): TypedApiResponse<TRes> {
  return {
    raw: res,
    status: () => res.status(),
    ok: () => res.ok(),
    headers: () => res.headers(),
    text: () => res.text(),
    json: () => res.json() as Promise<TRes>,
  };
}

export async function apiGet<TRes = unknown>(
  target: RequestTarget,
  path: EndpointPath<"get">,
  options?: Omit<TypedRequestOptions<never>, "data">,
): Promise<TypedApiResponse<TRes>> {
  const ctx = resolveRequestContext(target);
  const res = await ctx.get(path, {
    headers: buildHeaders(options),
    timeout: options?.timeout,
  });
  return wrapResponse<TRes>(res);
}

export async function apiPost<TRes = unknown, TBody = Record<string, unknown>>(
  target: RequestTarget,
  path: EndpointPath<"post">,
  options?: TypedRequestOptions<TBody>,
): Promise<TypedApiResponse<TRes>> {
  const ctx = resolveRequestContext(target);
  const res = await ctx.post(path, {
    headers: buildHeaders(options),
    data: options?.data,
    timeout: options?.timeout,
  });
  return wrapResponse<TRes>(res);
}

export async function apiPut<TRes = unknown, TBody = Record<string, unknown>>(
  target: RequestTarget,
  path: EndpointPath<"put">,
  options?: TypedRequestOptions<TBody>,
): Promise<TypedApiResponse<TRes>> {
  const ctx = resolveRequestContext(target);
  const res = await ctx.put(path, {
    headers: buildHeaders(options),
    data: options?.data,
    timeout: options?.timeout,
  });
  return wrapResponse<TRes>(res);
}

export async function apiPatch<TRes = unknown, TBody = Record<string, unknown>>(
  target: RequestTarget,
  path: EndpointPath<"patch">,
  options?: TypedRequestOptions<TBody>,
): Promise<TypedApiResponse<TRes>> {
  const ctx = resolveRequestContext(target);
  const res = await ctx.patch(path, {
    headers: buildHeaders(options),
    data: options?.data,
    timeout: options?.timeout,
  });
  return wrapResponse<TRes>(res);
}

export async function apiDelete<TRes = unknown, TBody = Record<string, unknown>>(
  target: RequestTarget,
  path: EndpointPath<"delete">,
  options?: TypedRequestOptions<TBody>,
): Promise<TypedApiResponse<TRes>> {
  const ctx = resolveRequestContext(target);
  const res = await ctx.delete(path, {
    headers: buildHeaders(options),
    data: options?.data,
    timeout: options?.timeout,
  });
  return wrapResponse<TRes>(res);
}

/**
 * Évince tous les caches RAM côté API (`POST /api/v1/_e2e/evict-memory-caches`),
 * vide optionnellement le stockage navigateur, puis recharge la page depuis PostgreSQL 18.
 */
export async function reloadColdFromPg(
  page: Page,
  options: { readonly clearBrowserStorage?: boolean } = {},
): Promise<void> {
  // Wait for initial shell/login/Day-0 mount so any in-flight GET /api/v1/auth/session
  // commits its rotated Set-Cookie before evicting backend RAM and reloading.
  await page
    .locator(
      '[data-testid="four-zone-direction-c-shell"], [data-testid="login-page-container"], [data-testid="first-boot-admin-setup-modal"]',
    )
    .first()
    .waitFor({ state: "visible", timeout: 10000 })
    .catch(() => undefined);
  if (options.clearBrowserStorage !== false) {
    await page.evaluate(() => {
      window.localStorage.clear();
      window.sessionStorage.clear();
    });
  }
  const evictRes = await apiPost<ApiSchemaComponents["EvictMemoryCachesResponse"]>(
    page,
    "/api/v1/_e2e/evict-memory-caches",
  );
  expect(
    evictRes.status(),
    "POST /api/v1/_e2e/evict-memory-caches doit retourner 200 en ORCIA_ENV=e2e",
  ).toBe(200);
  const body = await evictRes.json();
  expect(body.evicted).toBe(true);
  await page.reload({ waitUntil: "domcontentloaded" });
}
