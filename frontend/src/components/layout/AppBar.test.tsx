import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useThemeStore } from "../../store/themeStore";
import { useViewStore } from "../../store/viewStore";
import { AppBar } from "./AppBar";

vi.mock("../../api/settings", () => ({
  useSetTheme: () => ({ mutate: vi.fn() }),
}));

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
      ],
    },
  }),
  useSwitchWorkspace: () => ({ mutate: vi.fn() }),
  useCreateWorkspace: () => ({ mutate: vi.fn() }),
  useRegisterWorkspace: () => ({ mutate: vi.fn() }),
  useForgetWorkspace: () => ({ mutate: vi.fn() }),
}));

describe("AppBar", () => {
  beforeEach(() => {
    useViewStore.setState({ view: "workspace" });
    useThemeStore.setState({ theme: "system", systemDark: false });
  });

  it("renders Workspace and Tutorial tabs", () => {
    render(<AppBar />);
    expect(
      screen.getByRole("button", { name: "Workspace" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Tutorial" }),
    ).toBeInTheDocument();
  });

  it("clicking Tutorial switches the view", async () => {
    render(<AppBar />);
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Tutorial" }));
    expect(useViewStore.getState().view).toBe("tutorial");
  });

  it("has exactly one theme toggle", () => {
    render(<AppBar />);
    expect(screen.getAllByLabelText(/theme/i)).toHaveLength(1);
  });
});
