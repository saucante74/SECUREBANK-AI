import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "../api/client";
import { askRag } from "../api/services";
import type { RagAskResponse } from "../api/types";
import {
  apiErrorTranslationKey,
  type ApiErrorTranslationKey,
} from "../i18n/apiErrorKeys";

interface RagRequestState {
  errorKey?: ApiErrorTranslationKey;
  isLoading: boolean;
  response?: RagAskResponse;
}

interface RagRequestController extends RagRequestState {
  reset: () => void;
  submit: (question: string, token: string) => Promise<void>;
}

export function useRagRequest(): RagRequestController {
  const [state, setState] = useState<RagRequestState>({ isLoading: false });
  const abortControllerRef = useRef<AbortController | undefined>(undefined);
  const requestSequenceRef = useRef(0);

  const reset = useCallback(() => {
    requestSequenceRef.current += 1;
    abortControllerRef.current?.abort();
    abortControllerRef.current = undefined;
    setState({ isLoading: false });
  }, []);

  useEffect(() => {
    return () => {
      requestSequenceRef.current += 1;
      abortControllerRef.current?.abort();
    };
  }, []);

  const submit = useCallback(async (question: string, token: string) => {
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    const requestSequence = requestSequenceRef.current + 1;
    requestSequenceRef.current = requestSequence;
    abortControllerRef.current = controller;
    setState({ isLoading: true });

    try {
      const response = await askRag(
        { question },
        token,
        undefined,
        controller.signal,
      );
      if (requestSequenceRef.current !== requestSequence) {
        return;
      }
      setState({ isLoading: false, response });
    } catch (error: unknown) {
      if (requestSequenceRef.current !== requestSequence) {
        return;
      }
      if (error instanceof ApiError && error.category === "aborted") {
        setState({ isLoading: false });
        return;
      }
      const errorKey =
        error instanceof ApiError
          ? apiErrorTranslationKey(error.category)
          : apiErrorTranslationKey("http");
      setState({ errorKey, isLoading: false });
    } finally {
      if (requestSequenceRef.current === requestSequence) {
        abortControllerRef.current = undefined;
      }
    }
  }, []);

  return { ...state, reset, submit };
}
