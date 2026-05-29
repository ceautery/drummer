import { create } from "zustand";
import type { ThemePref } from "../types";

export type ResolvedTheme = "light" | "dark";

export function resolveTheme(
  theme: ThemePref,
  systemDark: boolean,
): ResolvedTheme {
  if (theme === "system") return systemDark ? "dark" : "light";
  return theme;
}

interface ThemeState {
  theme: ThemePref;
  systemDark: boolean;
  setTheme: (theme: ThemePref) => void;
  setSystemDark: (systemDark: boolean) => void;
}

export const useThemeStore = create<ThemeState>()((set) => ({
  theme: "system",
  systemDark: false,
  setTheme: (theme) => set({ theme }),
  setSystemDark: (systemDark) => set({ systemDark }),
}));

export function useResolvedTheme(): ResolvedTheme {
  const theme = useThemeStore((s) => s.theme);
  const systemDark = useThemeStore((s) => s.systemDark);
  return resolveTheme(theme, systemDark);
}
