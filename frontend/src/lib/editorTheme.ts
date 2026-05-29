import type { Extension } from "@codemirror/state";
import { oneDark } from "@codemirror/theme-one-dark";
import type { ResolvedTheme } from "../store/themeStore";

/** CodeMirror theme extension for the resolved app theme. Light = built-in default. */
export function editorThemeExtension(resolved: ResolvedTheme): Extension {
  return resolved === "dark" ? oneDark : [];
}
