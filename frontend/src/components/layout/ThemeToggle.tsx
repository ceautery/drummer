import type * as React from "react";
import { useMemo } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useSetTheme } from "../../api/settings";
import { useThemeStore } from "../../store/themeStore";
import type { ThemePref } from "../../types";

const ICON: Record<ThemePref, string> = {
  light: "☀️",
  dark: "🌙",
  system: "🖥️",
};

const ORDER: ThemePref[] = ["light", "dark", "system"];

export function ThemeToggle() {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useSetTheme();

  const itemLabels = useMemo<Record<string, React.ReactNode>>(
    () => ({
      light: <span>☀️</span>,
      dark: <span>🌙</span>,
      system: <span>🖥️</span>,
    }),
    [],
  );

  const handleChange = (value: string | null) => {
    if (value === null) return;
    setTheme.mutate(value as ThemePref);
  };

  return (
    <Select value={theme} onValueChange={handleChange} items={itemLabels}>
      <SelectTrigger size="sm" className="w-auto" aria-label="Theme">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {ORDER.map((mode) => (
          <SelectItem key={mode} value={mode}>
            <span className="flex items-center gap-2 capitalize">
              <span>{ICON[mode]}</span>
              {mode}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
