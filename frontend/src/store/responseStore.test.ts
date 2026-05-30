import { beforeEach, describe, expect, it } from "vitest";
import { useResponseStore } from "./responseStore";

describe("responseStore.setRequestInfo", () => {
  beforeEach(() => {
    useResponseStore.getState().reset();
  });

  it("stores the sent request, warnings, and variables", () => {
    useResponseStore.getState().setRequestInfo(
      {
        method: "GET",
        url: "https://x/{{missing}}",
        params: { q: "1" },
        headers: { Accept: "application/json" },
        body: "",
      },
      ["missing"],
      { base_url: "https://x" },
    );
    const s = useResponseStore.getState();
    expect(s.sentRequest?.url).toBe("https://x/{{missing}}");
    expect(s.warnings).toEqual(["missing"]);
    expect(s.variablesUsed).toEqual({ base_url: "https://x" });
  });

  it("reset clears the request info", () => {
    useResponseStore
      .getState()
      .setRequestInfo(
        { method: "GET", url: "https://x", params: {}, headers: {}, body: "" },
        ["w"],
        { a: "b" },
      );
    useResponseStore.getState().reset();
    const s = useResponseStore.getState();
    expect(s.sentRequest).toBeNull();
    expect(s.warnings).toEqual([]);
    expect(s.variablesUsed).toEqual({});
  });
});
