import type { ApiErrorCategory } from "../api/client";

export type ApiErrorTranslationKey =
  | "errors.unauthenticated"
  | "errors.forbidden"
  | "errors.validation"
  | "errors.upstreamService"
  | "errors.serviceUnavailable"
  | "errors.network"
  | "errors.aborted"
  | "errors.unexpectedResponse"
  | "errors.http";

const errorTranslationKeys: Record<
  ApiErrorCategory,
  ApiErrorTranslationKey
> = {
  unauthenticated: "errors.unauthenticated",
  forbidden: "errors.forbidden",
  validation: "errors.validation",
  upstream_service: "errors.upstreamService",
  service_unavailable: "errors.serviceUnavailable",
  network: "errors.network",
  aborted: "errors.aborted",
  unexpected_response: "errors.unexpectedResponse",
  http: "errors.http",
};

export function apiErrorTranslationKey(
  category: ApiErrorCategory,
): ApiErrorTranslationKey {
  return errorTranslationKeys[category];
}
