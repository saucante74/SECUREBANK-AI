export type ApiErrorCategory =
  | "unauthenticated"
  | "forbidden"
  | "validation"
  | "upstream_service"
  | "service_unavailable"
  | "network"
  | "aborted"
  | "unexpected_response"
  | "http";

export type HttpMethod = "GET" | "POST";

export interface ApiErrorContext {
  category: ApiErrorCategory;
  method: HttpMethod;
  status?: number;
  cause?: unknown;
}

const userMessages: Record<ApiErrorCategory, string> = {
  unauthenticated: "Une authentification est requise.",
  forbidden: "Vous n’avez pas l’autorisation d’effectuer cette action.",
  validation: "Les informations envoyées ne sont pas valides.",
  upstream_service: "Le service de génération ne peut pas répondre actuellement.",
  service_unavailable: "Le service est temporairement indisponible.",
  network: "La connexion au service a échoué.",
  aborted: "La requête a été annulée.",
  unexpected_response: "Le service a renvoyé une réponse inattendue.",
  http: "La requête n’a pas pu aboutir.",
};

export class ApiError extends Error {
  readonly category: ApiErrorCategory;
  readonly method: HttpMethod;
  readonly status?: number;

  constructor(context: ApiErrorContext) {
    super(userMessages[context.category], { cause: context.cause });
    this.name = "ApiError";
    this.category = context.category;
    this.method = context.method;
    this.status = context.status;
  }
}

export type FetchImplementation = typeof fetch;

export interface ApiRequestOptions {
  csrfToken?: string;
  signal?: AbortSignal;
  token?: string;
}

export interface ApiPostOptions extends ApiRequestOptions {
  body: unknown;
}

export interface ApiClient {
  get<ResponseBody>(path: string, options?: ApiRequestOptions): Promise<ResponseBody>;
  post<ResponseBody>(path: string, options: ApiPostOptions): Promise<ResponseBody>;
}

function categoryFromStatus(status: number): ApiErrorCategory {
  if (status === 401) return "unauthenticated";
  if (status === 403) return "forbidden";
  if (status === 422) return "validation";
  if (status === 502) return "upstream_service";
  if (status === 503) return "service_unavailable";
  return "http";
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

async function readJson<ResponseBody>(
  response: Response,
  method: HttpMethod,
): Promise<ResponseBody> {
  const body = await response.text();

  if (!response.ok) {
    throw new ApiError({
      category: categoryFromStatus(response.status),
      method,
      status: response.status,
    });
  }

  if (!body.trim()) {
    if (response.status === 204) {
      return undefined as ResponseBody;
    }
    throw new ApiError({
      category: "unexpected_response",
      method,
      status: response.status,
    });
  }

  try {
    return JSON.parse(body) as ResponseBody;
  } catch (error: unknown) {
    throw new ApiError({
      category: "unexpected_response",
      method,
      status: response.status,
      cause: error,
    });
  }
}

export function createApiClient(
  fetchImplementation: FetchImplementation = globalThis.fetch,
  basePath = "/api",
): ApiClient {
  async function request<ResponseBody>(
    method: HttpMethod,
    path: string,
    options: ApiRequestOptions,
    body?: unknown,
  ): Promise<ResponseBody> {
    const headers = new Headers({ Accept: "application/json" });

    if (options.token) {
      headers.set("Authorization", `Bearer ${options.token}`);
    }
    if (options.csrfToken) {
      headers.set("X-CSRF-Token", options.csrfToken);
    }
    if (body !== undefined) {
      headers.set("Content-Type", "application/json");
    }

    try {
      const response = await fetchImplementation(`${basePath}${path}`, {
        method,
        credentials: "include",
        headers,
        signal: options.signal,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      return await readJson<ResponseBody>(response, method);
    } catch (error: unknown) {
      if (error instanceof ApiError) throw error;
      if (isAbortError(error)) {
        throw new ApiError({ category: "aborted", method, cause: error });
      }
      throw new ApiError({ category: "network", method, cause: error });
    }
  }

  return {
    get: <ResponseBody>(path: string, options: ApiRequestOptions = {}) =>
      request<ResponseBody>("GET", path, options),
    post: <ResponseBody>(path: string, options: ApiPostOptions) =>
      request<ResponseBody>("POST", path, options, options.body),
  };
}
