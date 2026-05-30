import { useRequestStore } from "../../store/requestStore";
import type { RequestSummary } from "../../types";

const METHOD_COLOURS: Record<string, string> = {
  GET: "text-green-600 dark:text-green-400",
  POST: "text-blue-600 dark:text-blue-400",
  PUT: "text-amber-600 dark:text-amber-400",
  PATCH: "text-orange-500 dark:text-orange-400",
  DELETE: "text-red-600 dark:text-red-400",
  HEAD: "text-muted-foreground",
  OPTIONS: "text-muted-foreground",
  TRACE: "text-muted-foreground",
};

interface TreeNodeProps {
  request: RequestSummary;
  onSelect: (path: string) => void;
  onDelete: (path: string) => void;
}

export function TreeNode({ request, onSelect, onDelete }: TreeNodeProps) {
  const { selectedPath, isDirty } = useRequestStore();
  const isSelected = selectedPath === request.path;
  const dirty = isSelected && isDirty();

  return (
    <div
      className={`group flex w-full items-center rounded ${
        isSelected ? "bg-primary/10" : "hover:bg-muted"
      }`}
    >
      <button
        type="button"
        className={`flex flex-1 items-center gap-2 px-2 py-1 text-left text-sm ${
          isSelected ? "text-primary" : "text-foreground"
        }`}
        onClick={() => onSelect(request.path)}
        data-testid={`tree-node-${request.path}`}
      >
        <span
          className={`w-14 shrink-0 text-xs font-mono font-semibold ${METHOD_COLOURS[request.method] ?? "text-muted-foreground"}`}
        >
          {request.method}
        </span>
        <span className="flex-1 truncate">{request.name}</span>
        {dirty && (
          <span
            className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500"
            title="Unsaved changes"
          />
        )}
      </button>
      <button
        type="button"
        aria-label={`Delete ${request.name}`}
        className="px-1.5 text-xs text-muted-foreground opacity-0 hover:text-red-600 group-hover:opacity-100 group-focus-within:opacity-100"
        onClick={() => onDelete(request.path)}
      >
        ✕
      </button>
    </div>
  );
}
