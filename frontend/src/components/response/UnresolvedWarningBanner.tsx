import { useResponseStore } from "../../store/responseStore";

export function UnresolvedWarningBanner() {
  const warnings = useResponseStore((s) => s.warnings);
  if (warnings.length === 0) return null;
  return (
    <div
      role="alert"
      className="border-b border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-700 dark:text-amber-400"
    >
      ⚠ Unresolved variables:{" "}
      <span className="font-mono">
        {warnings.map((w) => `{{${w}}}`).join(", ")}
      </span>
    </div>
  );
}
