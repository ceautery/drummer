import { beforeEach, describe, expect, it } from "vitest";
import type { RequestDetail } from "../types";
import { useRequestStore } from "./requestStore";

const makeDetail = (url = "http://example.com"): RequestDetail => ({
  path: "users/list.md",
  frontmatter: {
    name: "List Users",
    method: "GET",
    url,
    headers: {},
    params: {},
    encoding: "utf-8",
    cookies: { mode: "session", cookies: {} },
    auth: {
      type: "none",
      token: "",
      username: "",
      password: "",
      key: "",
      value: "",
      token_url: "",
      client_id: "",
      client_secret: "",
      scope: "",
    },
    pre_script: "",
    post_script: "",
    script_timeout_ms: null,
    tags: [],
    skip: false,
  },
  body: "",
});

beforeEach(() => {
  useRequestStore.setState({
    selectedPath: null,
    saved: null,
    draft: null,
    activeTab: "params",
  });
});

describe("requestStore", () => {
  it("starts clean", () => {
    const s = useRequestStore.getState();
    expect(s.selectedPath).toBeNull();
    expect(s.isDirty()).toBe(false);
  });

  it("load sets saved and clears draft", () => {
    const detail = makeDetail();
    useRequestStore.getState().load(detail);
    const s = useRequestStore.getState();
    expect(s.saved).toEqual(detail);
    expect(s.draft).toBeNull();
    expect(s.isDirty()).toBe(false);
  });

  it("patch creates a draft and marks dirty", () => {
    useRequestStore.getState().load(makeDetail());
    useRequestStore.getState().patch({ url: "http://changed.example.com" });
    const s = useRequestStore.getState();
    expect(s.draft?.frontmatter.url).toBe("http://changed.example.com");
    expect(s.isDirty()).toBe(true);
  });

  it("discard clears draft", () => {
    useRequestStore.getState().load(makeDetail());
    useRequestStore.getState().patch({ url: "http://changed.example.com" });
    useRequestStore.getState().discard();
    expect(useRequestStore.getState().isDirty()).toBe(false);
    expect(useRequestStore.getState().draft).toBeNull();
  });

  it("markSaved clears draft after save", () => {
    const detail = makeDetail();
    useRequestStore.getState().load(detail);
    useRequestStore.getState().patch({ url: "http://changed.example.com" });
    const updated = {
      ...detail,
      frontmatter: { ...detail.frontmatter, url: "http://changed.example.com" },
    };
    useRequestStore.getState().markSaved(updated);
    expect(useRequestStore.getState().isDirty()).toBe(false);
    expect(useRequestStore.getState().draft).toBeNull();
  });

  it("deselect clears selection, saved, and draft", () => {
    useRequestStore.getState().select("users/list.md");
    useRequestStore.getState().load(makeDetail());
    useRequestStore.getState().patch({ url: "http://changed.example.com" });
    useRequestStore.getState().deselect();
    const s = useRequestStore.getState();
    expect(s.selectedPath).toBeNull();
    expect(s.saved).toBeNull();
    expect(s.draft).toBeNull();
  });
});
