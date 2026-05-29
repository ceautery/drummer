import { useEffect } from "react";
import { useResolvedTheme, useThemeStore } from "../store/themeStore";

/** Subscribes to the OS preference and reflects the resolved theme onto <html>. */
export function useApplyTheme(): void {
  const setSystemDark = useThemeStore((s) => s.setSystemDark);
  const resolved = useResolvedTheme();

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    setSystemDark(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setSystemDark(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [setSystemDark]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", resolved === "dark");
  }, [resolved]);
}
