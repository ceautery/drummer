import { create } from "zustand";

export const DEFAULT_ENVIRONMENT = "local";

interface SessionState {
  activeEnvironment: string;
  variables: Record<string, string>;
  setActiveEnvironment: (name: string) => void;
  setVariables: (vars: Record<string, string>) => void;
}

export const useSessionStore = create<SessionState>()((set) => ({
  activeEnvironment: DEFAULT_ENVIRONMENT,
  variables: {},
  setActiveEnvironment: (activeEnvironment) => set({ activeEnvironment }),
  setVariables: (variables) => set({ variables }),
}));
