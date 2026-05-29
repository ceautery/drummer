import { useViewStore } from "../../store/viewStore";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

export function AppBar() {
  const setView = useViewStore((s) => s.setView);
  return (
    <nav className="flex shrink-0 items-center gap-4 border-b bg-white px-4 py-2">
      <span className="text-sm font-semibold">🥁 Drummer</span>
      <WorkspaceSwitcher />
      <button
        type="button"
        onClick={() => setView("tutorial")}
        className="ml-auto rounded px-3 py-1 text-xs text-gray-500 hover:text-gray-800"
      >
        Tutorial
      </button>
    </nav>
  );
}
