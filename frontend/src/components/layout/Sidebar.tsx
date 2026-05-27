import { useEnvironments } from "../../api/environments";
import { useProjectStore } from "../../store/projectStore";
import { useSessionStore } from "../../store/sessionStore";
import { RequestTree } from "../tree/RequestTree";

interface SidebarProps {
  onRequestSelect: (path: string) => void;
}

export function Sidebar({ onRequestSelect }: SidebarProps) {
  const project = useProjectStore((s) => s.project);
  const requests = useProjectStore((s) => s.requests);
  const activeEnvironment = useSessionStore((s) => s.activeEnvironment);
  const setActiveEnvironment = useSessionStore((s) => s.setActiveEnvironment);
  const { data: environments = [] } = useEnvironments();

  return (
    <div className="flex h-full flex-col border-r bg-gray-50">
      <div className="border-b px-3 py-2">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          Project
        </p>
        <p className="truncate text-sm font-medium text-gray-900">
          {project?.name}
        </p>
      </div>

      {environments.length > 0 && (
        <div className="border-b px-3 py-2">
          <label htmlFor="environment-select" className="text-xs text-gray-500">
            Environment
          </label>
          <select
            id="environment-select"
            className="mt-1 w-full rounded border px-2 py-1 text-sm"
            value={activeEnvironment}
            onChange={(e) => setActiveEnvironment(e.target.value)}
          >
            {environments.map((env) => (
              <option key={env.name} value={env.name}>
                {env.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-1 py-1">
        <RequestTree requests={requests} onSelect={onRequestSelect} />
      </div>
    </div>
  );
}
