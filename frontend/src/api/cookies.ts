import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";

export function useCookies() {
  return useQuery<Record<string, Record<string, string>>>({
    queryKey: ["cookies"],
    queryFn: () =>
      apiFetch<Record<string, Record<string, string>>>("/api/cookies"),
  });
}

export function useClearCookies() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: () => apiFetch<void>("/api/cookies", { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["cookies"] });
    },
  });
}
