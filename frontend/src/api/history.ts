import { useQuery } from "@tanstack/react-query";
import type { HistoryRecord } from "../types";
import { apiFetch } from "./client";

export function useHistory(requestPath: string | null) {
  return useQuery<HistoryRecord[]>({
    queryKey: ["history", requestPath],
    queryFn: () =>
      apiFetch<HistoryRecord[]>(
        `/api/history?request_path=${encodeURIComponent(requestPath ?? "")}&limit=50`,
      ),
    enabled: requestPath !== null,
  });
}
