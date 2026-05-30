import { hexdump } from "../../lib/hexdump";

interface RawViewerProps {
  body: string | null;
}

export function RawViewer({ body }: RawViewerProps) {
  if (body === null) return null;
  const rows = hexdump(body);

  return (
    <div className="h-full overflow-auto p-2">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="border-b text-muted-foreground">
            <th className="px-2 py-1 text-left w-24">Offset</th>
            <th className="px-2 py-1 text-left">Hex</th>
            <th className="px-2 py-1 text-left w-32">ASCII</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.offset} className="border-b last:border-0">
              <td className="px-2 py-0.5 text-muted-foreground">
                {row.offset}
              </td>
              <td className="px-2 py-0.5 text-foreground">{row.hex}</td>
              <td className="px-2 py-0.5 text-muted-foreground">{row.ascii}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
