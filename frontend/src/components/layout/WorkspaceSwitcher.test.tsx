import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

vi.mock("../../api/workspaces", () => ({
  useWorkspaces: () => ({
    data: {
      active: "scratch",
      workspaces: [
        {
          id: "scratch",
          name: "Scratch",
          kind: "central",
          path: "/s",
          is_scratch: true,
        },
        {
          id: "my-api",
          name: "My API",
          kind: "central",
          path: "/m",
          is_scratch: false,
        },
      ],
    },
  }),
  useSwitchWorkspace: () => ({ mutate: vi.fn() }),
  useCreateWorkspace: () => ({ mutate: vi.fn() }),
  useRegisterWorkspace: () => ({ mutate: vi.fn() }),
}));

describe("WorkspaceSwitcher", () => {
  it("shows the active workspace in the trigger", () => {
    render(<WorkspaceSwitcher />);
    expect(screen.getByText(/Scratch/)).toBeInTheDocument();
  });
});
