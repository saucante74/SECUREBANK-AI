import { createApiClient, type ApiClient } from "./client";
import type {
  AuthMeResponse,
  HealthResponse,
  LoginRequest,
  RagAskRequest,
  RagAskResponse,
} from "./types";

const apiClient = createApiClient();

export function getHealth(
  client: ApiClient = apiClient,
  signal?: AbortSignal,
): Promise<HealthResponse> {
  return client.get<HealthResponse>("/health", { signal });
}

export function getCurrentUser(
  token?: string,
  client: ApiClient = apiClient,
  signal?: AbortSignal,
): Promise<AuthMeResponse> {
  return client.get<AuthMeResponse>("/auth/me", { token, signal });
}

export function loginUser(
  credentials: LoginRequest,
  client: ApiClient = apiClient,
  signal?: AbortSignal,
): Promise<AuthMeResponse> {
  return client.post<AuthMeResponse>("/auth/login", {
    body: credentials,
    signal,
  });
}

export function logoutUser(
  client: ApiClient = apiClient,
  signal?: AbortSignal,
): Promise<undefined> {
  return client.post<undefined>("/auth/logout", {
    body: undefined,
    csrfToken: readCookie("securebank_csrf"),
    signal,
  });
}

export function askRag(
  request: RagAskRequest,
  token?: string,
  client: ApiClient = apiClient,
  signal?: AbortSignal,
): Promise<RagAskResponse> {
  return client.post<RagAskResponse>("/rag/ask", {
    body: request,
    csrfToken: token ? undefined : readCookie("securebank_csrf"),
    token,
    signal,
  });
}

function readCookie(name: string): string | undefined {
  const prefix = `${encodeURIComponent(name)}=`;
  const cookie = document.cookie
    .split(";")
    .map((value) => value.trim())
    .find((value) => value.startsWith(prefix));
  if (!cookie) return undefined;
  return decodeURIComponent(cookie.slice(prefix.length));
}
