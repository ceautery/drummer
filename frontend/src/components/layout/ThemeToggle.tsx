import type * as React from "react";
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

const ITEM_LABELS: Record<string, React.ReactNode> = {
  light: <span>{ICON.light}</span>,
  dark: <span>{ICON.dark}</span>,
  system: <span>{ICON.system}</span>,
};

const ORDER: ThemePref[] = ["light", "dark", "system"];

const isThemePref = (v: string): v is ThemePref =>
  v === "light" || v === "dark" || v === "system";

export function ThemeToggle() {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useSetTheme();

  const handleChange = (value: string | null) => {
    if (value === null || !isThemePref(value)) return;
    setTheme.mutate(value);
  };

  return (
    <Select value={theme} onValueChange={handleChange} items={ITEM_LABELS}>
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
