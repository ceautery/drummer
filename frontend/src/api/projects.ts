import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ProjectInfo } from "../types";
import { apiFetch } from "./client";

export function useProject() {
  return useQuery<ProjectInfo | null>({
    queryKey: ["project"],
    queryFn: async () => {
      try {
        return await apiFetch<ProjectInfo>("/api/project");
      } catch {
        return null;
      }
    },
  });
}

export function useSetProject() {
  const queryClient = useQueryClient();
  return useMutation<ProjectInfo, Error, string>({
    mutationFn: (path) =>
      apiFetch<ProjectInfo>("/api/project", {
        method: "POST",
        body: JSON.stringify({ path }),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["project"], data);
      void queryClient.invalidateQueries({ queryKey: ["requests"] });
      void queryClient.invalidateQueries({ queryKey: ["environments"] });
    },
  });
}
