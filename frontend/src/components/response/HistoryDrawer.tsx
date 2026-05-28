import { useHistory } from "../../api/history";
import { useRequestStore } from "../../store/requestStore";
import { useResponseStore } from "../../store/responseStore";
import type { HistoryRecord } from "../../types";
import { StatusBadge } from "../shared/StatusBadge";

export function HistoryDrawer() {
  const { selectedPath } = useRequestStore();
  const responseStore = useResponseStore();
  const { data: records = [], isLoading } = useHistory(selectedPath);

  if (!selectedPath) {
    return <p className="p-3 text-xs text-gray-400">No request selected.</p>;
  }
  if (isLoading) {
    return <p className="p-3 text-xs text-gray-400">Loading…</p>;
  }
  if (records.length === 0) {
    return <p className="p-3 text-xs text-gray-400">No history yet.</p>;
  }

  const loadRecord = (rec: HistoryRecord) => {
    responseStore.setStatus(rec.status_code, rec.url);
    responseStore.setHeaders(rec.response_headers);
    responseStore.setBody(rec.response_body, rec.encoding, rec.elapsed_ms);
    responseStore.setDone(rec.id, [], null, null);
  };

  return (
    <div className="overflow-auto">
      {records.map((rec) => (
        <button
          key={rec.id}
          type="button"
          className="flex w-full items-center gap-3 border-b px-3 py-2 text-left hover:bg-gray-50"
          onClick={() => loadRecord(rec)}
        >
          <StatusBadge code={rec.status_code} />
          <span className="flex-1 truncate text-xs text-gray-600">
            {rec.url}
          </span>
          <span className="text-xs text-gray-400">
            {new Date(rec.sent_at).toLocaleTimeString()}
          </span>
        </button>
      ))}
    </div>
  );
}
