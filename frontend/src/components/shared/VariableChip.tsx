interface VariableChipProps {
  name: string;
  value: string | undefined;
}

export function VariableChip({ name, value }: VariableChipProps) {
  const isKnown = value !== undefined;
  return (
    <span
      className={`inline-block rounded px-1 text-xs font-mono ${
        isKnown
          ? "bg-purple-100 text-purple-700"
          : "bg-amber-100 text-amber-700"
      }`}
      title={isKnown ? value : "Not set"}
    >
      {`{{${name}}}`}
    </span>
  );
}
