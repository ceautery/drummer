import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EnvironmentManager } from "./EnvironmentManager";

const h = vi.hoisted(() => ({
  list: [
    { name: "local", variable_count: 1 },
    { name: "staging", variable_count: 0 },
  ],
  detail: { name: "local", variables: { base_url: "https://api" } },
  saveMutate: vi.fn(),
  createMutate: vi.fn(),
  deleteMutate: vi.fn(),
}));

vi.mock("../../api/environments", () => ({
  useEnvironments: () => ({ data: h.list }),
  useEnvironment: () => ({ data: h.detail }),
  useSaveEnvironment: () => ({ mutate: h.saveMutate }),
  useCreateEnvironment: () => ({ mutate: h.createMutate }),
  useDeleteEnvironment: () => ({ mutate: h.deleteMutate }),
}));

describe("EnvironmentManager", () => {
  beforeEach(() => {
    h.saveMutate.mockReset();
    h.createMutate.mockReset();
    h.deleteMutate.mockReset();
  });

  it("renders the selected environment's variables", () => {
    render(<EnvironmentManager open onClose={vi.fn()} />);
    expect(screen.getByDisplayValue("base_url")).toBeInTheDocument();
    expect(screen.getByDisplayValue("https://api")).toBeInTheDocument();
  });

  it("Save sends the edited variables", () => {
    render(<EnvironmentManager open onClose={vi.fn()} />);
    fireEvent.change(screen.getByDisplayValue("https://api"), {
      target: { value: "https://api/v2" },
    });
    fireEvent.click(screen.getByTestId("env-save-button"));
    expect(h.saveMutate).toHaveBeenCalledWith({
      name: "local",
      variables: { base_url: "https://api/v2" },
    });
  });

  it("+ New creates an environment from the prompted name", () => {
    vi.spyOn(window, "prompt").mockReturnValue("qa");
    render(<EnvironmentManager open onClose={vi.fn()} />);
    fireEvent.click(screen.getByTestId("env-new-button"));
    expect(h.createMutate.mock.calls[0]?.[0]).toEqual({
      name: "qa",
      variables: {},
    });
  });

  it("+ New shows an inline error for a duplicate name and does not create", () => {
    vi.spyOn(window, "prompt").mockReturnValue("staging");
    render(<EnvironmentManager open onClose={vi.fn()} />);
    fireEvent.click(screen.getByTestId("env-new-button"));
    expect(screen.getByRole("alert")).toHaveTextContent(/already exists/i);
    expect(h.createMutate).not.toHaveBeenCalled();
  });

  it("Delete removes the selected environment after confirm", () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<EnvironmentManager open onClose={vi.fn()} />);
    fireEvent.click(screen.getByTestId("env-delete-button"));
    expect(h.deleteMutate.mock.calls[0]?.[0]).toBe("local");
  });
});
