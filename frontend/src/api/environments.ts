import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { EnvironmentDetail, EnvironmentSummary } from "../types";
import { apiFetch } from "./client";

export function useEnvironments() {
  return useQuery<EnvironmentSummary[]>({
    queryKey: ["environments"],
    queryFn: () => apiFetch<EnvironmentSummary[]>("/api/environments"),
  });
}

export function useEnvironment(name: string | null) {
  return useQuery<EnvironmentDetail>({
    queryKey: ["environment", name],
    queryFn: () => apiFetch<EnvironmentDetail>(`/api/environments/${name}`),
    enabled: name !== null,
  });
}

export function useSaveEnvironment() {
  const queryClient = useQueryClient();
  return useMutation<EnvironmentDetail, Error, EnvironmentDetail>({
    mutationFn: (env) =>
      apiFetch<EnvironmentDetail>(`/api/environments/${env.name}`, {
        method: "PUT",
        body: JSON.stringify(env),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["environment", data.name], data);
    },
  });
}
