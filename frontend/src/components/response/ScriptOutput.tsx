import { useMemo } from "react";
import { useResponseStore } from "../../store/responseStore";
import type { StreamingState } from "../../types";

interface ScriptOutputViewProps {
  scriptLogs: string[];
  scriptError: string | null;
  scriptSuggestion: string | null;
  streaming: StreamingState;
}

export function ScriptOutputView({
  scriptLogs,
  scriptError,
  scriptSuggestion,
  streaming,
}: ScriptOutputViewProps) {
  const logEntries = useMemo(
    () => scriptLogs.map((text, i) => ({ key: `${i}:${text}`, text })),
    [scriptLogs],
  );

  const hasOutput = scriptLogs.length > 0 || scriptError !== null;

  if (streaming === "idle") {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-gray-400">
          Send a request to see script output.
        </p>
      </div>
    );
  }

  if (!hasOutput) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-gray-400">
          No script output for this request.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-3 font-mono text-xs">
      {logEntries.map(({ key, text }) => (
        <div key={key} className="py-0.5 text-gray-300">
          {text}
        </div>
      ))}
      {scriptError && <div className="mt-2 text-red-400">{scriptError}</div>}
      {scriptSuggestion && (
        <div className="mt-1 text-amber-400">Hint: {scriptSuggestion}</div>
      )}
    </div>
  );
}

export function ScriptOutput() {
  const scriptLogs = useResponseStore((s) => s.scriptLogs);
  const scriptError = useResponseStore((s) => s.scriptError);
  const scriptSuggestion = useResponseStore((s) => s.scriptSuggestion);
  const streaming = useResponseStore((s) => s.streaming);
  return (
    <ScriptOutputView
      scriptLogs={scriptLogs}
      scriptError={scriptError}
      scriptSuggestion={scriptSuggestion}
      streaming={streaming}
    />
  );
}
