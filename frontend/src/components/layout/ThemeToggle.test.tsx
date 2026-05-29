import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { useThemeStore } from "../../store/themeStore";
import { ThemeToggle } from "./ThemeToggle";

const mutate = vi.fn();
vi.mock("../../api/settings", () => ({
  useSetTheme: () => ({ mutate }),
}));

describe("ThemeToggle", () => {
  it("renders the trigger reflecting the active mode", () => {
    useThemeStore.setState({ theme: "dark", systemDark: false });
    render(<ThemeToggle />);
    expect(screen.getByLabelText(/theme/i)).toBeInTheDocument();
  });

  it("selecting an option calls setTheme with the chosen mode", async () => {
    useThemeStore.setState({ theme: "light", systemDark: false });
    render(<ThemeToggle />);
    const user = userEvent.setup();
    await user.click(screen.getByLabelText(/theme/i));
    await user.click(await screen.findByText(/dark/i));
    expect(mutate).toHaveBeenCalledWith("dark");
  });
});
