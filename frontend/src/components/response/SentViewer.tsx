import { useResponseStore } from "../../store/responseStore";

function maskAuth(value: string): string {
  const space = value.indexOf(" ");
  return space > 0 ? `${value.slice(0, space)} ••••••` : "••••••";
}

function Rows({ entries }: { entries: Record<string, string> }) {
  const pairs = Object.entries(entries);
  if (pairs.length === 0) {
    return <p className="px-2 text-xs text-muted-foreground">(none)</p>;
  }
  return (
    <table className="w-full text-xs font-mono">
      <tbody>
        {pairs.map(([k, v]) => (
          <tr key={k} className="border-b last:border-0">
            <td className="px-2 py-0.5 text-muted-foreground align-top w-1/3">
              {k}
            </td>
            <td className="px-2 py-0.5 text-foreground break-all">{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function SentViewer() {
  const sent = useResponseStore((s) => s.sentRequest);
  const variablesUsed = useResponseStore((s) => s.variablesUsed);

  if (!sent) {
    return (
      <p className="px-3 py-4 text-xs text-muted-foreground">
        No request was sent — a pre-request script failed before sending.
      </p>
    );
  }

  const displayHeaders: Record<string, string> = Object.fromEntries(
    Object.entries(sent.headers).map(([k, v]) => {
      const lower = k.toLowerCase();
      if (lower === "authorization") return [k, maskAuth(v)];
      if (lower === "cookie") return [k, "••••••"];
      return [k, v];
    }),
  );

  return (
    <div className="flex flex-col gap-3 p-2 text-sm">
      <div className="font-mono text-xs break-all">
        <span className="font-semibold">{sent.method}</span>{" "}
        <span className="text-foreground">{sent.url}</span>
      </div>
      <section>
        <h3 className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Params
        </h3>
        <Rows entries={sent.params} />
      </section>
      <section>
        <h3 className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Headers
        </h3>
        <Rows entries={displayHeaders} />
      </section>
      <section>
        <h3 className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Body
        </h3>
        {sent.body ? (
          <pre className="px-2 text-xs font-mono whitespace-pre-wrap break-all text-foreground">
            {sent.body}
          </pre>
        ) : (
          <p className="px-2 text-xs text-muted-foreground">(none)</p>
        )}
      </section>
      <section>
        <h3 className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Variables used
        </h3>
        <Rows entries={variablesUsed} />
      </section>
    </div>
  );
}
