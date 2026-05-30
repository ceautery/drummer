import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { useResponseStore } from "../../store/responseStore";
import { SentViewer } from "./SentViewer";

afterEach(() => {
  useResponseStore.getState().reset();
});

describe("SentViewer", () => {
  it("renders method, url, params and masks the Authorization header", () => {
    useResponseStore.getState().setRequestInfo(
      {
        method: "GET",
        url: "https://api.example.com/v1",
        params: { q: "search" },
        headers: {
          Accept: "application/json",
          Authorization: "Bearer secret-token",
        },
        body: "",
      },
      [],
      {},
    );
    render(<SentViewer />);
    expect(screen.getByText("https://api.example.com/v1")).toBeInTheDocument();
    expect(screen.getByText("search")).toBeInTheDocument();
    expect(screen.getByText("application/json")).toBeInTheDocument();
    expect(screen.queryByText(/secret-token/)).not.toBeInTheDocument();
  });

  it("shows a message when no request was sent", () => {
    useResponseStore.getState().setRequestInfo(null, [], {});
    render(<SentViewer />);
    expect(screen.getByText(/no request was sent/i)).toBeInTheDocument();
  });
});
