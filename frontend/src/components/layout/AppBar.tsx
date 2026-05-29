import { useViewStore } from "../../store/viewStore";
import { ThemeToggle } from "./ThemeToggle";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

export function AppBar() {
  const setView = useViewStore((s) => s.setView);
  return (
    <nav className="flex shrink-0 items-center gap-4 border-b bg-card px-4 py-2">
      <span className="text-sm font-semibold">🥁 Drummer</span>
      <WorkspaceSwitcher />
      <div className="ml-auto flex items-center gap-2">
        <button
          type="button"
          onClick={() => setView("tutorial")}
          className="rounded px-3 py-1 text-xs text-muted-foreground hover:text-foreground"
        >
          Tutorial
        </button>
        <ThemeToggle />
      </div>
    </nav>
  );
}
