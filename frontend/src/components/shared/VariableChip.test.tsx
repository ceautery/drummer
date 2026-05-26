import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VariableChip } from "./VariableChip";

describe("VariableChip", () => {
  it("renders the variable name", () => {
    render(<VariableChip name="base_url" value="http://localhost" />);
    expect(screen.getByText("{{base_url}}")).toBeInTheDocument();
  });

  it("shows resolved value as title when known", () => {
    render(<VariableChip name="token" value="abc123" />);
    expect(screen.getByTitle("abc123")).toBeInTheDocument();
  });

  it("shows 'Not set' as title when unknown", () => {
    render(<VariableChip name="missing" value={undefined} />);
    expect(screen.getByTitle("Not set")).toBeInTheDocument();
  });
});
