interface BodyViewerProps {
  body: string | null;
  contentType?: string;
}

function tryPrettyJson(text: string): string | null {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return null;
  }
}

export function BodyViewer({ body, contentType = "" }: BodyViewerProps) {
  if (body === null) return null;

  if (contentType.startsWith("image/")) {
    const src = `data:${contentType};base64,${btoa(body)}`;
    return (
      <div className="p-3">
        <img src={src} alt="Response" className="max-w-full" />
      </div>
    );
  }

  const isJson = contentType.includes("json") || contentType === "";
  const pretty = isJson ? tryPrettyJson(body) : null;
  const display = pretty ?? body;

  return (
    <pre className="overflow-auto p-3 text-xs font-mono whitespace-pre-wrap break-words text-gray-800">
      {display}
    </pre>
  );
}
