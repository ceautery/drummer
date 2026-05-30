import { beforeEach, describe, expect, it } from "vitest";
import { useRequestStore } from "./requestStore";

describe("requestStore.deselect", () => {
  beforeEach(() => {
    useRequestStore.setState({ selectedPath: null, saved: null, draft: null });
  });

  it("clears selection and loaded request", () => {
    useRequestStore.getState().select("foo.md");
    useRequestStore.getState().deselect();
    const s = useRequestStore.getState();
    expect(s.selectedPath).toBeNull();
    expect(s.saved).toBeNull();
    expect(s.draft).toBeNull();
  });
});
