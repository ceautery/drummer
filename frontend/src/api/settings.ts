import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useThemeStore } from "../store/themeStore";
import type { Settings, ThemePref } from "../types";
import { apiFetch } from "./client";

export function useSettings() {
  return useQuery<Settings>({
    queryKey: ["settings"],
    queryFn: () => apiFetch<Settings>("/api/settings"),
    staleTime: Number.POSITIVE_INFINITY,
  });
}

export function useSetTheme() {
  const qc = useQueryClient();
  const setTheme = useThemeStore((s) => s.setTheme);
  return useMutation<Settings, Error, ThemePref, { prev: ThemePref }>({
    mutationFn: (theme) =>
      apiFetch<Settings>("/api/settings", {
        method: "PUT",
        body: JSON.stringify({ theme }),
      }),
    onMutate: (theme) => {
      const prev = useThemeStore.getState().theme;
      setTheme(theme); // optimistic
      return { prev };
    },
    onError: (_err, _theme, context) => {
      if (context) setTheme(context.prev); // rollback
    },
    onSuccess: (data) => {
      setTheme(data.theme);
      void qc.invalidateQueries({ queryKey: ["settings"] });
    },
  });
}
