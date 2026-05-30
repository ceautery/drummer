import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { RequestDetail } from "../types";
import { apiFetch } from "./client";
import { useSaveRequest } from "./requests";

vi.mock("./client", () => ({ apiFetch: vi.fn() }));

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient();
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

function detail(): RequestDetail {
  return {
    path: "secure.md",
    body: "the body",
    frontmatter: {
      name: "Secure",
      method: "GET",
      url: "https://x.com",
      headers: {},
      params: { q: "search" },
      encoding: "utf-8",
      cookies: { mode: "session", cookies: {} },
      auth: {
        type: "bearer",
        token: "secret-token",
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
      post_script: "dm.log('x')",
      script_timeout_ms: null,
      tags: [],
      skip: false,
    },
  };
}

describe("useSaveRequest", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
  });

  it("PUTs the full frontmatter and body (no field loss)", async () => {
    const d = detail();
    vi.mocked(apiFetch).mockResolvedValue(d);
    const { result } = renderHook(() => useSaveRequest(), { wrapper });
    await result.current.mutateAsync({ path: "secure.md", detail: d });
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1));

    expect(apiFetch).toHaveBeenCalledWith(
      "/api/requests/secure.md",
      expect.objectContaining({ method: "PUT" }),
    );
    // Type-safe access to the request body (no tuple destructure — keeps tsc -b happy).
    const opts = vi.mocked(apiFetch).mock.calls[0]?.[1];
    const sent = JSON.parse(String(opts?.body));
    expect(sent.frontmatter.params).toEqual({ q: "search" });
    expect(sent.frontmatter.auth.token).toBe("secret-token");
    expect(sent.frontmatter.post_script).toBe("dm.log('x')");
    expect(sent.body).toBe("the body");
  });
});
