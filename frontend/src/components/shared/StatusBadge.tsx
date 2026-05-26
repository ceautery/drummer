interface StatusBadgeProps {
  code: number;
  className?: string;
}

function colourClass(code: number): string {
  if (code >= 200 && code < 300) return "bg-green-100 text-green-800";
  if (code >= 300 && code < 400) return "bg-yellow-100 text-yellow-800";
  return "bg-red-100 text-red-800";
}

export function StatusBadge({ code, className = "" }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-mono font-semibold ${colourClass(code)} ${className}`}
      data-testid="response-status"
    >
      {code}
    </span>
  );
}
