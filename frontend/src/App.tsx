import { useEffect } from "react";
import { useProject } from "./api/projects";
import { AppBar } from "./components/layout/AppBar";
import { useProjectStore } from "./store/projectStore";
import { useViewStore } from "./store/viewStore";
import { TutorialView } from "./views/TutorialView";
import { WorkspaceView } from "./views/WorkspaceView";

export default function App() {
  const view = useViewStore((s) => s.view);
  const { data: project, isLoading } = useProject();
  const setProject = useProjectStore((s) => s.setProject);

  useEffect(() => {
    if (project) setProject(project);
  }, [project, setProject]);

  if (view === "tutorial") return <TutorialView />;

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-gray-400">
        Loading…
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col">
      <AppBar />
      <div className="min-h-0 flex-1">
        <WorkspaceView />
      </div>
    </div>
  );
}
