import { render, screen } from "@testing-library/react";
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
});
