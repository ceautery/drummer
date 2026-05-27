import { Plus, Trash2 } from "lucide-react";

interface KeyValueTableProps {
  entries: Record<string, string>;
  onChange: (entries: Record<string, string>) => void;
  keyPlaceholder?: string;
  valuePlaceholder?: string;
}

export function KeyValueTable({
  entries,
  onChange,
  keyPlaceholder = "Key",
  valuePlaceholder = "Value",
}: KeyValueTableProps) {
  const pairs = Object.entries(entries);

  const update = (index: number, key: string, value: string) => {
    const next = [...pairs];
    next[index] = [key, value];
    onChange(Object.fromEntries(next.filter(([k]) => k !== "")));
  };

  const remove = (index: number) => {
    const next = pairs.filter((_, i) => i !== index);
    onChange(Object.fromEntries(next));
  };

  const add = () => {
    onChange({ ...entries, "": "" });
  };

  return (
    <div className="flex flex-col gap-1 p-2">
      {pairs.map(([k, v], i) => (
        <div key={k || String(i)} className="flex items-center gap-1">
          <input
            className="flex-1 rounded border px-2 py-1 text-sm font-mono"
            value={k}
            placeholder={keyPlaceholder}
            onChange={(e) => update(i, e.target.value, v)}
          />
          <input
            className="flex-1 rounded border px-2 py-1 text-sm font-mono"
            value={v}
            placeholder={valuePlaceholder}
            onChange={(e) => update(i, k, e.target.value)}
          />
          <button
            type="button"
            className="p-1 text-gray-400 hover:text-red-500"
            onClick={() => remove(i)}
            aria-label="Remove"
          >
            <Trash2 size={14} />
          </button>
        </div>
      ))}
      <button
        type="button"
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-purple-600 mt-1"
        onClick={add}
      >
        <Plus size={13} /> Add
      </button>
    </div>
  );
}
