import { useViewStore } from "../../store/viewStore";
import { ThemeToggle } from "./ThemeToggle";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

const TABS = [
  { id: "workspace", label: "Workspace" },
  { id: "tutorial", label: "Tutorial" },
] as const;

export function AppBar() {
  const view = useViewStore((s) => s.view);
  const setView = useViewStore((s) => s.setView);
  return (
    <nav className="flex shrink-0 items-center gap-4 border-b bg-card px-4 py-2">
      <span className="text-sm font-semibold">🥁 Drummer</span>
      <div className="flex gap-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setView(tab.id)}
            className={`rounded px-3 py-1 text-xs ${
              view === tab.id
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <WorkspaceSwitcher />
      <div className="ml-auto flex items-center gap-2">
        <ThemeToggle />
      </div>
    </nav>
  );
}
