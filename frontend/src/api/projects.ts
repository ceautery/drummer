import { useQuery } from "@tanstack/react-query";
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
