import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { useWorkspaces } from "../../api/workspaces";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

vi.mock("../../api/workspaces", () => ({
  useWorkspaces: vi.fn(() => ({
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
  })),
  useSwitchWorkspace: () => ({ mutate: vi.fn() }),
  useCreateWorkspace: () => ({ mutate: vi.fn() }),
  useRegisterWorkspace: () => ({ mutate: vi.fn() }),
  useForgetWorkspace: () => ({ mutate: vi.fn() }),
}));

describe("WorkspaceSwitcher", () => {
  it("shows the active workspace in the trigger", () => {
    render(<WorkspaceSwitcher />);
    expect(screen.getByText(/Scratch/)).toBeInTheDocument();
  });

  it("does not offer Forget when the active workspace is not external", () => {
    render(<WorkspaceSwitcher />);
    expect(
      screen.queryByText(/Forget external workspace/),
    ).not.toBeInTheDocument();
  });

  it("offers Forget when the active workspace is external", async () => {
    vi.mocked(useWorkspaces).mockReturnValueOnce({
      data: {
        active: "/ext/repo",
        workspaces: [
          {
            id: "scratch",
            name: "Scratch",
            kind: "central",
            path: "/s",
            is_scratch: true,
          },
          {
            id: "/ext/repo",
            name: "Ext Repo",
            kind: "external",
            path: "/ext/repo",
            is_scratch: false,
          },
        ],
      },
    } as unknown as ReturnType<typeof useWorkspaces>);
    render(<WorkspaceSwitcher />);
    await userEvent.setup().click(screen.getByRole("combobox"));
    expect(screen.getByText(/Forget external workspace/)).toBeInTheDocument();
  });
});
