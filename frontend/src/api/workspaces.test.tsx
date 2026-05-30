import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "./client";
import { useForgetWorkspace } from "./workspaces";

vi.mock("./client", () => ({ apiFetch: vi.fn() }));

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient();
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useForgetWorkspace", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
  });

  it("POSTs the workspace id to /api/workspaces/forget", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      workspaces: [],
      active: "scratch",
    });
    const { result } = renderHook(() => useForgetWorkspace(), { wrapper });
    await result.current.mutateAsync("/abs/path");
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1));
    const [url, opts] = vi.mocked(apiFetch).mock.calls[0]!;
    expect(url).toBe("/api/workspaces/forget");
    expect(opts?.method).toBe("POST");
    expect(JSON.parse(opts?.body as string)).toEqual({ id: "/abs/path" });
  });
});
