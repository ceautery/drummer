import { useRequestStore } from "../../store/requestStore";
import { KeyValueTable } from "./KeyValueTable";

export function HeadersTab() {
  const { saved, draft, patch } = useRequestStore();
  const current = draft ?? saved;
  const headers = current?.frontmatter.headers ?? {};

  return (
    <KeyValueTable
      entries={headers}
      onChange={(headers) => patch({ headers })}
      keyPlaceholder="Header"
      valuePlaceholder="Value"
    />
  );
}
