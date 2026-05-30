import { Settings } from "lucide-react";
import { useState } from "react";
import { useEnvironments } from "../../api/environments";
import { useProjectStore } from "../../store/projectStore";
import { useSessionStore } from "../../store/sessionStore";
import { RequestTree } from "../tree/RequestTree";
import { EnvironmentManager } from "./EnvironmentManager";

interface SidebarProps {
  onRequestSelect: (path: string) => void;
  onRequestDelete: (path: string) => void;
  onNewRequest: () => void;
}

export function Sidebar({
  onRequestSelect,
  onRequestDelete,
  onNewRequest,
}: SidebarProps) {
  const project = useProjectStore((s) => s.project);
  const requests = useProjectStore((s) => s.requests);
  const activeEnvironment = useSessionStore((s) => s.activeEnvironment);
  const setActiveEnvironment = useSessionStore((s) => s.setActiveEnvironment);
  const { data: environments = [] } = useEnvironments();
  const [manageOpen, setManageOpen] = useState(false);

  return (
    <div className="flex h-full flex-col border-r bg-sidebar">
      <div className="border-b px-3 py-2">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Project
        </p>
        <p className="truncate text-sm font-medium text-foreground">
          {project?.name}
        </p>
      </div>

      <div className="border-b px-3 py-2">
        <div className="flex items-center justify-between">
          <label
            htmlFor="environment-select"
            className="text-xs text-muted-foreground"
          >
            Environment
          </label>
          <button
            type="button"
            className="rounded p-0.5 text-muted-foreground hover:text-foreground"
            onClick={() => setManageOpen(true)}
            aria-label="Manage environments"
            data-testid="manage-environments-button"
          >
            <Settings size={14} />
          </button>
        </div>
        {environments.length > 0 && (
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
        )}
      </div>

      <div className="flex items-center justify-between border-b px-3 py-1.5">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Requests
        </span>
        <button
          type="button"
          className="rounded px-1.5 py-0.5 text-xs text-primary hover:bg-primary/10"
          onClick={onNewRequest}
          data-testid="new-request-button"
        >
          + New
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-1 py-1">
        <RequestTree
          requests={requests}
          onSelect={onRequestSelect}
          onDelete={onRequestDelete}
        />
      </div>

      <EnvironmentManager
        open={manageOpen}
        onClose={() => setManageOpen(false)}
      />
    </div>
  );
}
