import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RawViewer } from "./RawViewer";

describe("RawViewer", () => {
  it("renders the body text exactly once (hexdump ASCII column only)", () => {
    render(<RawViewer body="hello" />);
    // Before the fix the body appeared twice: once in the hexdump ASCII
    // column and once in a standalone <pre> panel. It must now appear once.
    expect(screen.getAllByText("hello")).toHaveLength(1);
  });

  it("renders a hexdump table with an Offset header", () => {
    render(<RawViewer body="hello" />);
    expect(screen.getByText("Offset")).toBeInTheDocument();
  });

  it("renders nothing when body is null", () => {
    const { container } = render(<RawViewer body={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
