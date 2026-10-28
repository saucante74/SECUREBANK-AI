import { createApiClient, type ApiClient } from "./client";
import type {
  AuthMeResponse,
  HealthResponse,
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
  token: string,
  client: ApiClient = apiClient,
  signal?: AbortSignal,
): Promise<AuthMeResponse> {
  return client.get<AuthMeResponse>("/auth/me", { token, signal });
}

export function askRag(
  request: RagAskRequest,
  token: string,
  client: ApiClient = apiClient,
  signal?: AbortSignal,
): Promise<RagAskResponse> {
  return client.post<RagAskResponse>("/rag/ask", {
    body: request,
    token,
    signal,
  });
}
