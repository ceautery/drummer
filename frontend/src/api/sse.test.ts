import { describe, expect, it, vi } from "vitest";
import type { ResponseState } from "../store/responseStore";
import { consumeSSE } from "./sse";

function sseResponse(blocks: string[]): Response {
  return new Response(`${blocks.join("\n\n")}\n\n`);
}

describe("consumeSSE request event", () => {
  it("dispatches setRequestInfo with sent, warnings, variables", async () => {
    const setRequestInfo = vi.fn();
    const stub = { setRequestInfo } as unknown as ResponseState;
    const payload = {
      sent: {
        method: "GET",
        url: "https://x/{{m}}",
        params: {},
        headers: {},
        body: "",
      },
      warnings: ["m"],
      variables: { a: "b" },
    };
    const res = sseResponse([
      `event: request\ndata: ${JSON.stringify(payload)}`,
    ]);
    await consumeSSE(res, stub);
    expect(setRequestInfo).toHaveBeenCalledWith(payload.sent, ["m"], {
      a: "b",
    });
  });
});
