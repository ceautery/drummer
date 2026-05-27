import { useEffect } from "react";
import { useProject } from "./api/projects";
import { useProjectStore } from "./store/projectStore";
import { WelcomeView } from "./views/WelcomeView";
import { WorkspaceView } from "./views/WorkspaceView";

export default function App() {
  const { data: project, isLoading } = useProject();
  const setProject = useProjectStore((s) => s.setProject);

  useEffect(() => {
    if (project) setProject(project);
  }, [project, setProject]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-gray-400 text-sm">
        Loading…
      </div>
    );
  }

  if (!project) return <WelcomeView />;
  return <WorkspaceView />;
}
