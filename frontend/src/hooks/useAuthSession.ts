import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../api/client";
import { getCurrentUser, loginUser, logoutUser } from "../api/services";
import type { AuthMeResponse, LoginRequest } from "../api/types";
import {
  apiErrorTranslationKey,
  type ApiErrorTranslationKey,
} from "../i18n/apiErrorKeys";

export type AuthStatus = "checking" | "anonymous" | "authenticated";

interface AuthSessionController {
  clearVersion: number;
  expireSession: () => void;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  logoutErrorKey?: ApiErrorTranslationKey;
  status: AuthStatus;
  user?: AuthMeResponse;
}

export function useAuthSession(): AuthSessionController {
  const [status, setStatus] = useState<AuthStatus>("checking");
  const [user, setUser] = useState<AuthMeResponse | undefined>();
  const [clearVersion, setClearVersion] = useState(0);
  const [logoutErrorKey, setLogoutErrorKey] =
    useState<ApiErrorTranslationKey>();
  useEffect(() => {
    let isActive = true;
    const controller = new AbortController();

    void getCurrentUser(undefined, undefined, controller.signal)
      .then((identity) => {
        if (!isActive) return;
        setUser(identity);
        setStatus("authenticated");
      })
      .catch(() => {
        if (!isActive) return;
        setUser(undefined);
        setStatus("anonymous");
      });

    return () => {
      isActive = false;
      controller.abort();
    };
  }, []);

  const login = useCallback(async (credentials: LoginRequest) => {
    const identity = await loginUser(credentials);
    setUser(identity);
    setStatus("authenticated");
    setLogoutErrorKey(undefined);
  }, []);

  const expireSession = useCallback(() => {
    setUser(undefined);
    setStatus("anonymous");
  }, []);

  const logout = useCallback(async () => {
    setLogoutErrorKey(undefined);
    try {
      await logoutUser();
      setUser(undefined);
      setStatus("anonymous");
      setClearVersion((version) => version + 1);
    } catch (error: unknown) {
      if (error instanceof ApiError && error.category === "unauthenticated") {
        setUser(undefined);
        setStatus("anonymous");
        setClearVersion((version) => version + 1);
        return;
      }
      setLogoutErrorKey(
        error instanceof ApiError
          ? apiErrorTranslationKey(error.category)
          : apiErrorTranslationKey("http"),
      );
    }
  }, []);

  return {
    clearVersion,
    expireSession,
    login,
    logout,
    logoutErrorKey,
    status,
    user,
  };
}
