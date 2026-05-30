import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { RequestDetail, RequestSummary } from "../types";
import { apiFetch } from "./client";

export function useRequests(options?: { enabled?: boolean }) {
  return useQuery<RequestSummary[]>({
    queryKey: ["requests"],
    queryFn: () => apiFetch<RequestSummary[]>("/api/requests"),
    enabled: options?.enabled ?? false,
  });
}

export function useRequest(path: string | null) {
  return useQuery<RequestDetail>({
    queryKey: ["request", path],
    queryFn: () => apiFetch<RequestDetail>(`/api/requests/${path}`),
    enabled: path !== null,
  });
}

export function useSaveRequest() {
  const queryClient = useQueryClient();
  return useMutation<
    RequestDetail,
    Error,
    { path: string; detail: RequestDetail }
  >({
    mutationFn: ({ path, detail }) =>
      apiFetch<RequestDetail>(`/api/requests/${path}`, {
        method: "PUT",
        body: JSON.stringify({
          frontmatter: detail.frontmatter,
          body: detail.body,
        }),
      }),
    onSuccess: (data, { path }) => {
      queryClient.setQueryData(["request", path], data);
      void queryClient.invalidateQueries({ queryKey: ["requests"] });
    },
  });
}

export function useDeleteRequest() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (path) =>
      apiFetch<void>(`/api/requests/${path}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["requests"] });
    },
  });
}
