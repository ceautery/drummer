import {
  type QueryClient,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { WorkspaceInfo, WorkspaceListResponse } from "../types";
import { apiFetch } from "./client";

export function useWorkspaces() {
  return useQuery<WorkspaceListResponse>({
    queryKey: ["workspaces"],
    queryFn: () => apiFetch<WorkspaceListResponse>("/api/workspaces"),
  });
}

function invalidateWorkspaceData(qc: QueryClient) {
  void qc.invalidateQueries({ queryKey: ["workspaces"] });
  void qc.invalidateQueries({ queryKey: ["project"] });
  void qc.invalidateQueries({ queryKey: ["requests"] });
  void qc.invalidateQueries({ queryKey: ["environments"] });
  void qc.invalidateQueries({ queryKey: ["history"] });
}

export function useSwitchWorkspace() {
  const qc = useQueryClient();
  return useMutation<WorkspaceInfo, Error, string>({
    mutationFn: (id) =>
      apiFetch<WorkspaceInfo>("/api/workspaces/active", {
        method: "POST",
        body: JSON.stringify({ id }),
      }),
    onSuccess: () => invalidateWorkspaceData(qc),
  });
}

export function useCreateWorkspace() {
  const qc = useQueryClient();
  return useMutation<WorkspaceInfo, Error, string>({
    mutationFn: (name) =>
      apiFetch<WorkspaceInfo>("/api/workspaces", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    onSuccess: () => invalidateWorkspaceData(qc),
  });
}

export function useRegisterWorkspace() {
  const qc = useQueryClient();
  return useMutation<WorkspaceInfo, Error, string>({
    mutationFn: (path) =>
      apiFetch<WorkspaceInfo>("/api/workspaces/register", {
        method: "POST",
        body: JSON.stringify({ path }),
      }),
    onSuccess: () => invalidateWorkspaceData(qc),
  });
}

export function useForgetWorkspace() {
  const qc = useQueryClient();
  return useMutation<WorkspaceListResponse, Error, string>({
    mutationFn: (id) =>
      apiFetch<WorkspaceListResponse>("/api/workspaces/forget", {
        method: "POST",
        body: JSON.stringify({ id }),
      }),
    onSuccess: () => invalidateWorkspaceData(qc),
  });
}
