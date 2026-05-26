import { create } from "zustand";
import type { ProjectInfo, RequestSummary } from "../types";

interface ProjectState {
  project: ProjectInfo | null;
  requests: RequestSummary[];
  setProject: (project: ProjectInfo) => void;
  setRequests: (requests: RequestSummary[]) => void;
  clear: () => void;
}

export const useProjectStore = create<ProjectState>()((set) => ({
  project: null,
  requests: [],
  setProject: (project) => set({ project }),
  setRequests: (requests) => set({ requests }),
  clear: () => set({ project: null, requests: [] }),
}));
