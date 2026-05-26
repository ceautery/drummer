import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("shows 2xx as green", () => {
    render(<StatusBadge code={200} />);
    const el = screen.getByText("200");
    expect(el.className).toMatch(/green/);
  });

  it("shows 3xx as yellow", () => {
    render(<StatusBadge code={301} />);
    const el = screen.getByText("301");
    expect(el.className).toMatch(/yellow/);
  });

  it("shows 4xx as red", () => {
    render(<StatusBadge code={404} />);
    const el = screen.getByText("404");
    expect(el.className).toMatch(/red/);
  });

  it("shows 5xx as red", () => {
    render(<StatusBadge code={500} />);
    const el = screen.getByText("500");
    expect(el.className).toMatch(/red/);
  });
});
