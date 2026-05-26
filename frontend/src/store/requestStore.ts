import { create } from "zustand";
import type { RequestDetail, RequestFrontmatter, RequestTab } from "../types";

interface RequestState {
  selectedPath: string | null;
  saved: RequestDetail | null;
  draft: RequestDetail | null;
  activeTab: RequestTab;
  select: (path: string) => void;
  load: (detail: RequestDetail) => void;
  patch: (changes: Partial<RequestFrontmatter> & { body?: string }) => void;
  discard: () => void;
  markSaved: (detail: RequestDetail) => void;
  setTab: (tab: RequestTab) => void;
  isDirty: () => boolean;
}

export const useRequestStore = create<RequestState>()((set, get) => ({
  selectedPath: null,
  saved: null,
  draft: null,
  activeTab: "params",

  select: (path) => set({ selectedPath: path, draft: null }),

  load: (detail) => set({ saved: detail, draft: null }),

  patch: (changes) => {
    const { saved, draft } = get();
    const base = draft ?? saved;
    if (!base) return;
    const { body: bodyVal, ...fmChanges } = changes;
    set({
      draft: {
        ...base,
        frontmatter: { ...base.frontmatter, ...fmChanges },
        body: bodyVal !== undefined ? bodyVal : base.body,
      },
    });
  },

  discard: () => set({ draft: null }),

  markSaved: (detail) => set({ saved: detail, draft: null }),

  setTab: (tab) => set({ activeTab: tab }),

  isDirty: () => {
    const { saved, draft } = get();
    if (!draft) return false;
    return JSON.stringify(draft) !== JSON.stringify(saved);
  },
}));
