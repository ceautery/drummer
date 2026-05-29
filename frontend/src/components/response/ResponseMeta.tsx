import type { StreamingState } from "../../types";
import { StatusBadge } from "../shared/StatusBadge";

interface ResponseMetaProps {
  statusCode: number | null;
  elapsedMs: number | null;
  bodyLength: number | null;
  streaming: StreamingState;
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

export function ResponseMeta({
  statusCode,
  elapsedMs,
  bodyLength,
  streaming,
}: ResponseMetaProps) {
  if (streaming === "idle") {
    return (
      <div className="flex items-center px-3 py-2 text-xs text-muted-foreground border-b">
        Send a request to see the response.
      </div>
    );
  }

  if (streaming === "streaming" && !statusCode) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 border-b">
        <span className="text-xs text-muted-foreground animate-pulse">
          Waiting…
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 px-3 py-2 border-b">
      {statusCode && <StatusBadge code={statusCode} />}
      {elapsedMs !== null && (
        <span className="text-xs text-muted-foreground">
          {elapsedMs.toFixed(0)} ms
        </span>
      )}
      {bodyLength !== null && (
        <span className="text-xs text-muted-foreground">
          {formatBytes(bodyLength)}
        </span>
      )}
      {streaming === "streaming" && (
        <span className="text-xs text-muted-foreground animate-pulse">
          streaming…
        </span>
      )}
    </div>
  );
}
