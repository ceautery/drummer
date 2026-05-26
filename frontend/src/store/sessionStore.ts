import { create } from "zustand";

interface SessionState {
  activeEnvironment: string;
  variables: Record<string, string>;
  setActiveEnvironment: (name: string) => void;
  setVariables: (vars: Record<string, string>) => void;
}

export const useSessionStore = create<SessionState>()((set) => ({
  activeEnvironment: "local",
  variables: {},
  setActiveEnvironment: (activeEnvironment) => set({ activeEnvironment }),
  setVariables: (variables) => set({ variables }),
}));
