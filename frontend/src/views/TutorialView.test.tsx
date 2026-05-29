import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useThemeStore } from "../store/themeStore";
import { TutorialView } from "./TutorialView";

vi.mock("../api/settings", () => ({
  useSetTheme: () => ({ mutate: vi.fn() }),
}));

function renderTutorial() {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <TutorialView />
    </QueryClientProvider>,
  );
}

describe("TutorialView", () => {
  beforeEach(() => {
    useThemeStore.setState({ theme: "system", systemDark: false });
  });

  it("renders the theme toggle in its nav", () => {
    renderTutorial();
    expect(screen.getByLabelText(/theme/i)).toBeInTheDocument();
  });

  it("is not hardcoded to a dark background", () => {
    const { container } = renderTutorial();
    const root = container.querySelector("div");
    expect(root?.className).not.toContain("bg-gray-950");
  });
});
