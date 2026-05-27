import { hexdump } from "../../lib/hexdump";

interface RawViewerProps {
  body: string | null;
}

export function RawViewer({ body }: RawViewerProps) {
  if (body === null) return null;
  const rows = hexdump(body);

  return (
    <div className="flex h-full overflow-hidden">
      <div className="flex-1 overflow-auto p-2">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="border-b text-gray-400">
              <th className="px-2 py-1 text-left w-24">Offset</th>
              <th className="px-2 py-1 text-left">Hex</th>
              <th className="px-2 py-1 text-left w-32">ASCII</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.offset} className="border-b last:border-0">
                <td className="px-2 py-0.5 text-gray-400">{row.offset}</td>
                <td className="px-2 py-0.5 text-gray-700">{row.hex}</td>
                <td className="px-2 py-0.5 text-gray-600">{row.ascii}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="w-72 border-l overflow-auto p-2">
        <pre className="text-xs font-mono whitespace-pre-wrap break-words text-gray-700">
          {body}
        </pre>
      </div>
    </div>
  );
}
