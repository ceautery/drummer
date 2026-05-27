import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { UrlBar } from "./UrlBar";

describe("UrlBar", () => {
  it("renders the method selector and Send button", () => {
    render(
      <UrlBar
        method="GET"
        url=""
        onMethodChange={vi.fn()}
        onUrlChange={vi.fn()}
        onSend={vi.fn()}
        onCancel={vi.fn()}
        isStreaming={false}
        variables={{}}
      />,
    );
    expect(screen.getByText("GET")).toBeInTheDocument();
    expect(screen.getByText("Send")).toBeInTheDocument();
  });

  it("calls onSend when Send is clicked", () => {
    const onSend = vi.fn();
    render(
      <UrlBar
        method="GET"
        url="http://example.com"
        onMethodChange={vi.fn()}
        onUrlChange={vi.fn()}
        onSend={onSend}
        onCancel={vi.fn()}
        isStreaming={false}
        variables={{}}
      />,
    );
    fireEvent.click(screen.getByText("Send"));
    expect(onSend).toHaveBeenCalledOnce();
  });

  it("shows Cancel when streaming", () => {
    render(
      <UrlBar
        method="POST"
        url=""
        onMethodChange={vi.fn()}
        onUrlChange={vi.fn()}
        onSend={vi.fn()}
        onCancel={vi.fn()}
        isStreaming={true}
        variables={{}}
      />,
    );
    expect(screen.getByText("Cancel")).toBeInTheDocument();
    expect(screen.queryByText("Send")).toBeNull();
  });
});
