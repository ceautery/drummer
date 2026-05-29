import type { ResponseState } from "../store/responseStore";

export async function* parseSSE(
  response: Response,
): AsyncGenerator<{ event: string; data: string }> {
  const reader = response.body?.getReader();
  if (!reader) return;
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE blocks are separated by a blank line (LF or CRLF)
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      const lines = block.trim().split(/\r?\n/);
      let event = "message";
      let data = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) event = line.slice(7).trim();
        else if (line.startsWith("data: ")) data = line.slice(6);
      }
      if (data) yield { event, data };
    }
  }
}

export async function consumeSSE(
  res: Response,
  response: ResponseState,
  onDone?: () => void,
): Promise<void> {
  for await (const { event, data } of parseSSE(res)) {
    const payload = JSON.parse(data) as unknown;
    if (event === "status") {
      const p = payload as { status_code: number; url: string };
      response.setStatus(p.status_code, p.url);
    } else if (event === "headers") {
      response.setHeaders(payload as [string, string][]);
    } else if (event === "body") {
      const p = payload as {
        body: string;
        encoding: string;
        elapsed_ms: number;
      };
      response.setBody(p.body, p.encoding, p.elapsed_ms);
    } else if (event === "done") {
      const p = payload as {
        history_id: string | null;
        script_logs: string[];
        script_error: string | null;
        script_suggestion: string | null;
      };
      response.setDone(
        p.history_id,
        p.script_logs ?? [],
        p.script_error ?? null,
        p.script_suggestion ?? null,
      );
      onDone?.();
    } else if (event === "error") {
      const p = payload as { message: string };
      response.setError(p.message);
    }
  }
}
