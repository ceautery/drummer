import { useEffect } from "react";
import { useProject } from "./api/projects";
import { useSettings } from "./api/settings";
import { AppBar } from "./components/layout/AppBar";
import { useApplyTheme } from "./lib/useApplyTheme";
import { useProjectStore } from "./store/projectStore";
import { useThemeStore } from "./store/themeStore";
import { useViewStore } from "./store/viewStore";
import { TutorialView } from "./views/TutorialView";
import { WorkspaceView } from "./views/WorkspaceView";

export default function App() {
  const view = useViewStore((s) => s.view);
  const { data: project, isLoading } = useProject();
  const { data: settings, isLoading: settingsLoading } = useSettings();
  const setProject = useProjectStore((s) => s.setProject);
  const setTheme = useThemeStore((s) => s.setTheme);

  useApplyTheme();

  useEffect(() => {
    if (project) setProject(project);
  }, [project, setProject]);

  useEffect(() => {
    if (settings) setTheme(settings.theme);
  }, [settings, setTheme]);

  if (settingsLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col">
      <AppBar />
      <div className="min-h-0 flex-1">
        {view === "tutorial" ? (
          <TutorialView />
        ) : isLoading ? (
          <div className="flex h-full items-center justify-center bg-background text-sm text-muted-foreground">
            Loading…
          </div>
        ) : (
          <WorkspaceView />
        )}
      </div>
    </div>
  );
}
