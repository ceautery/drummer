import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TutorialStep } from "../types";
import { TutorialView } from "./TutorialView";

const STEPS: TutorialStep[] = [
  {
    title: "Welcome to Drummer",
    instructions: "Welcome to the tutorial.",
    method: null,
    url: "",
    params: {},
    headers: {},
    body: "",
    pre_script: "",
    post_script: "",
    variable_overrides: {},
  },
  {
    title: "Your first GET request",
    instructions: "The simplest request is a GET.",
    method: "GET",
    url: "http://localhost:8000/mock/met/departments",
    params: {},
    headers: {},
    body: "",
    pre_script: "",
    post_script: "",
    variable_overrides: {},
  },
];

vi.mock("../api/tutorial", async (importActual) => {
  const actual = await importActual<typeof import("../api/tutorial")>();
  return {
    ...actual,
    useTutorialSteps: () => ({ data: STEPS }),
    useTutorialSend: () => ({ send: vi.fn(), cancel: vi.fn() }),
  };
});

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
    vi.clearAllMocks();
  });

  it("lists step titles in the coach rail", () => {
    renderTutorial();
    expect(screen.getByText("Welcome to Drummer")).toBeInTheDocument();
    expect(screen.getByText("Your first GET request")).toBeInTheDocument();
  });

  it("has no theme toggle (it lives in the AppBar now)", () => {
    renderTutorial();
    expect(screen.queryByLabelText(/theme/i)).not.toBeInTheDocument();
  });

  it("shows a placeholder on a no-request step", () => {
    renderTutorial();
    expect(screen.getByText(/no request/i)).toBeInTheDocument();
  });

  it("mounts the real request workbench on a request step", async () => {
    renderTutorial();
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: /Your first GET request/ }));
    expect(screen.getByRole("button", { name: "Params" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Script Output" }),
    ).toBeInTheDocument();
  });
});
