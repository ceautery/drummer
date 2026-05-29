import { useQuery } from "@tanstack/react-query";
import { useCallback, useRef } from "react";
import { useResponseStore } from "../store/responseStore";
import type { RequestDetail, TutorialStep } from "../types";
import { apiFetch } from "./client";
import { consumeSSE } from "./sse";

export function useTutorialSteps() {
  return useQuery<TutorialStep[]>({
    queryKey: ["tutorial-steps"],
    queryFn: () => apiFetch<TutorialStep[]>("/api/tutorial/steps"),
    staleTime: Number.POSITIVE_INFINITY,
  });
}

export function useTutorialSend() {
  const abortRef = useRef<AbortController | null>(null);
  const response = useResponseStore();

  const send = useCallback(
    async (stepIndex: number) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      response.reset();
      response.setStreaming("streaming");

      try {
        const res = await fetch(`/api/tutorial/steps/${stepIndex}/send`, {
          method: "POST",
          signal: controller.signal,
        });
        await consumeSSE(res, response);
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          response.setError(String(err));
          response.setStreaming("error");
        }
      }
    },
    [response],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    response.setStreaming("idle");
  }, [response]);

  return { send, cancel };
}

// Builds a display-only RequestDetail so the real request panes can render a
// tutorial step. The actual send goes through /api/tutorial/steps/{i}/send,
// which rebuilds the request from the backend STEPS, so these defaults are
// purely cosmetic.
export function stepToRequestDetail(step: TutorialStep): RequestDetail {
  return {
    path: "<tutorial>",
    body: step.body,
    frontmatter: {
      name: step.title,
      method: step.method ?? "GET",
      url: step.url,
      headers: step.headers,
      params: step.params,
      encoding: "utf-8",
      cookies: { mode: "session", cookies: {} },
      auth: {
        type: "none",
        token: "",
        username: "",
        password: "",
        key: "",
        value: "",
        token_url: "",
        client_id: "",
        client_secret: "",
        scope: "",
      },
      pre_script: step.pre_script,
      post_script: step.post_script,
      script_timeout_ms: null,
      tags: [],
      skip: false,
    },
  };
}
