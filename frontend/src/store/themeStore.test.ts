import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { resolveTheme, useResolvedTheme, useThemeStore } from "./themeStore";

describe("themeStore", () => {
  beforeEach(() => {
    useThemeStore.setState({ theme: "system", systemDark: false });
  });

  it("resolves explicit modes to themselves", () => {
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });

  it("resolves system to the OS preference", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
  });

  it("setTheme updates the store", () => {
    useThemeStore.getState().setTheme("dark");
    expect(useThemeStore.getState().theme).toBe("dark");
  });

  it("useResolvedTheme derives from store state", () => {
    const { result } = renderHook(() => useResolvedTheme());
    expect(result.current).toBe("light");
    act(() => {
      useThemeStore.setState({ systemDark: true });
    });
    expect(result.current).toBe("dark");
    act(() => {
      useThemeStore.setState({ theme: "light", systemDark: true });
    });
    expect(result.current).toBe("light");
  });
});
