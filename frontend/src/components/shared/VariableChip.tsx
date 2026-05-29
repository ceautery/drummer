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
          ? "bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300"
          : "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300"
      }`}
      title={isKnown ? value : "Not set"}
    >
      {`{{${name}}}`}
    </span>
  );
}
