import { create } from "zustand";

type AppView = "workspace" | "tutorial";

interface ViewState {
  view: AppView;
  setView: (v: AppView) => void;
}

export const useViewStore = create<ViewState>()((set) => ({
  view: "workspace",
  setView: (view) => set({ view }),
}));
