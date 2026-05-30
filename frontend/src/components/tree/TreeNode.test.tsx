import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { RequestSummary } from "../../types";
import { TreeNode } from "./TreeNode";

const request: RequestSummary = {
  path: "hello/get-hello.md",
  name: "Get Hello",
  method: "GET",
  url: "https://x.com",
};

describe("TreeNode", () => {
  it("calls onSelect when the row is clicked", () => {
    const onSelect = vi.fn();
    render(
      <TreeNode request={request} onSelect={onSelect} onDelete={vi.fn()} />,
    );
    fireEvent.click(screen.getByText("Get Hello"));
    expect(onSelect).toHaveBeenCalledWith("hello/get-hello.md");
  });

  it("calls onDelete (and not onSelect) when delete is clicked", () => {
    const onSelect = vi.fn();
    const onDelete = vi.fn();
    render(
      <TreeNode request={request} onSelect={onSelect} onDelete={onDelete} />,
    );
    fireEvent.click(screen.getByLabelText("Delete Get Hello"));
    expect(onDelete).toHaveBeenCalledWith("hello/get-hello.md");
    expect(onSelect).not.toHaveBeenCalled();
  });
});
