import { useRequestStore } from "../../store/requestStore";
import type { RequestSummary } from "../../types";

const METHOD_COLOURS: Record<string, string> = {
  GET: "text-green-600",
  POST: "text-blue-600",
  PUT: "text-amber-600",
  PATCH: "text-orange-500",
  DELETE: "text-red-600",
  HEAD: "text-gray-500",
  OPTIONS: "text-gray-500",
  TRACE: "text-gray-500",
};

interface TreeNodeProps {
  request: RequestSummary;
  onSelect: (path: string) => void;
}

export function TreeNode({ request, onSelect }: TreeNodeProps) {
  const { selectedPath, isDirty } = useRequestStore();
  const isSelected = selectedPath === request.path;
  const dirty = isSelected && isDirty();

  return (
    <button
      type="button"
      className={`flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm ${
        isSelected
          ? "bg-purple-50 text-purple-900"
          : "hover:bg-gray-100 text-gray-700"
      }`}
      onClick={() => onSelect(request.path)}
      data-testid={`tree-node-${request.path}`}
    >
      <span
        className={`w-14 shrink-0 text-xs font-mono font-semibold ${METHOD_COLOURS[request.method] ?? "text-gray-500"}`}
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
  );
}
