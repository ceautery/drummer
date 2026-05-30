import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "./client";
import { useCreateEnvironment, useDeleteEnvironment } from "./environments";

vi.mock("./client", () => ({ apiFetch: vi.fn() }));

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient();
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useCreateEnvironment", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
  });

  it("POSTs name and variables to /api/environments", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      name: "staging",
      variables: { a: "b" },
    });
    const { result } = renderHook(() => useCreateEnvironment(), { wrapper });
    await result.current.mutateAsync({
      name: "staging",
      variables: { a: "b" },
    });
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1));
    expect(apiFetch).toHaveBeenCalledWith(
      "/api/environments",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "staging", variables: { a: "b" } }),
      }),
    );
  });
});

describe("useDeleteEnvironment", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
  });

  it("DELETEs /api/environments/{name}", async () => {
    vi.mocked(apiFetch).mockResolvedValue(undefined);
    const { result } = renderHook(() => useDeleteEnvironment(), { wrapper });
    await result.current.mutateAsync("staging");
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1));
    expect(apiFetch).toHaveBeenCalledWith(
      "/api/environments/staging",
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});
