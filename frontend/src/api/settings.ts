import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useThemeStore } from "../store/themeStore";
import type { Settings, ThemePref } from "../types";
import { apiFetch } from "./client";

export function useSettings() {
  return useQuery<Settings>({
    queryKey: ["settings"],
    queryFn: () => apiFetch<Settings>("/api/settings"),
  });
}

export function useSetTheme() {
  const qc = useQueryClient();
  const setTheme = useThemeStore((s) => s.setTheme);
  return useMutation<Settings, Error, ThemePref>({
    mutationFn: (theme) => {
      setTheme(theme); // optimistic: apply immediately
      return apiFetch<Settings>("/api/settings", {
        method: "PUT",
        body: JSON.stringify({ theme }),
      });
    },
    onSuccess: (data) => {
      setTheme(data.theme);
      void qc.invalidateQueries({ queryKey: ["settings"] });
    },
  });
}
