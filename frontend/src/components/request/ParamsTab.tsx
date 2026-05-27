import { useRequestStore } from "../../store/requestStore";
import { KeyValueTable } from "./KeyValueTable";

export function ParamsTab() {
  const { saved, draft, patch } = useRequestStore();
  const current = draft ?? saved;
  const params = current?.frontmatter.params ?? {};

  return (
    <KeyValueTable
      entries={params}
      onChange={(params) => patch({ params })}
      keyPlaceholder="Parameter"
      valuePlaceholder="Value"
    />
  );
}
