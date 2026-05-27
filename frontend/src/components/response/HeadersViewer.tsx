interface HeadersViewerProps {
  headers: [string, string][];
}

export function HeadersViewer({ headers }: HeadersViewerProps) {
  if (headers.length === 0) {
    return <p className="p-3 text-xs text-gray-400">No headers.</p>;
  }

  return (
    <table className="w-full text-xs font-mono">
      <tbody>
        {headers.map(([k, v], i) => (
          <tr key={k + String(i)} className="border-b last:border-0">
            <td className="py-1 px-3 font-semibold text-gray-600 w-1/3 align-top">
              {k}
            </td>
            <td className="py-1 px-3 text-gray-800 break-all">{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
