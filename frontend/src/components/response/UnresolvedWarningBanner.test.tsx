import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { useResponseStore } from "../../store/responseStore";
import { UnresolvedWarningBanner } from "./UnresolvedWarningBanner";

afterEach(() => {
  useResponseStore.getState().reset();
});

describe("UnresolvedWarningBanner", () => {
  it("renders the unresolved variable names when warnings exist", () => {
    useResponseStore
      .getState()
      .setRequestInfo(
        { method: "GET", url: "x", params: {}, headers: {}, body: "" },
        ["api_key", "host"],
        {},
      );
    render(<UnresolvedWarningBanner />);
    expect(screen.getByRole("alert")).toHaveTextContent("api_key");
    expect(screen.getByRole("alert")).toHaveTextContent("host");
  });

  it("renders nothing when there are no warnings", () => {
    const { container } = render(<UnresolvedWarningBanner />);
    expect(container).toBeEmptyDOMElement();
  });
});
