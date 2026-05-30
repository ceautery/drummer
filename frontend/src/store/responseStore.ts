import { create } from "zustand";
import type { ResponseTab, SentRequest, StreamingState } from "../types";

export interface ResponseState {
  streaming: StreamingState;
  statusCode: number | null;
  url: string | null;
  responseHeaders: [string, string][];
  body: string | null;
  encoding: string | null;
  elapsedMs: number | null;
  error: string | null;
  historyId: string | null;
  activeTab: ResponseTab;
  scriptLogs: string[];
  scriptError: string | null;
  scriptSuggestion: string | null;
  sentRequest: SentRequest | null;
  warnings: string[];
  variablesUsed: Record<string, string>;

  reset: () => void;
  setStreaming: (state: StreamingState) => void;
  setStatus: (statusCode: number, url: string) => void;
  setHeaders: (headers: [string, string][]) => void;
  setBody: (body: string, encoding: string, elapsedMs: number) => void;
  setDone: (
    historyId: string | null,
    scriptLogs: string[],
    scriptError: string | null,
    scriptSuggestion: string | null,
  ) => void;
  setError: (error: string) => void;
  setTab: (tab: ResponseTab) => void;
  setRequestInfo: (
    sent: SentRequest | null,
    warnings: string[],
    variables: Record<string, string>,
  ) => void;
}

const initialState = {
  streaming: "idle" as StreamingState,
  statusCode: null,
  url: null,
  responseHeaders: [] as [string, string][],
  body: null,
  encoding: null,
  elapsedMs: null,
  error: null,
  historyId: null,
  activeTab: "body" as ResponseTab,
  scriptLogs: [] as string[],
  scriptError: null,
  scriptSuggestion: null,
  sentRequest: null as SentRequest | null,
  warnings: [] as string[],
  variablesUsed: {} as Record<string, string>,
};

export const useResponseStore = create<ResponseState>()((set) => ({
  ...initialState,
  reset: () => set({ ...initialState, activeTab: "body" }),
  setStreaming: (streaming) => set({ streaming }),
  setStatus: (statusCode, url) => set({ statusCode, url }),
  setHeaders: (responseHeaders) => set({ responseHeaders }),
  setBody: (body, encoding, elapsedMs) => set({ body, encoding, elapsedMs }),
  setDone: (historyId, scriptLogs, scriptError, scriptSuggestion) =>
    set({
      historyId,
      streaming: "done",
      scriptLogs,
      scriptError,
      scriptSuggestion,
    }),
  setError: (error) => set({ error, streaming: "error" }),
  setTab: (activeTab) => set({ activeTab }),
  setRequestInfo: (sentRequest, warnings, variablesUsed) =>
    set({ sentRequest, warnings, variablesUsed }),
}));
