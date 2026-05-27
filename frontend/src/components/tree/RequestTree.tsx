import type { RequestSummary } from "../../types";
import { TreeNode } from "./TreeNode";

interface RequestTreeProps {
  requests: RequestSummary[];
  onSelect: (path: string) => void;
}

export function RequestTree({ requests, onSelect }: RequestTreeProps) {
  if (requests.length === 0) {
    return (
      <p className="px-2 py-4 text-xs text-gray-400">No requests found.</p>
    );
  }

  return (
    <div className="flex flex-col gap-0.5 py-1" data-testid="request-tree">
      {requests.map((r) => (
        <TreeNode key={r.path} request={r} onSelect={onSelect} />
      ))}
    </div>
  );
}
