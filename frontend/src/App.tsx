import { useProject } from "./api/projects";
import { WelcomeView } from "./views/WelcomeView";

export default function App() {
  const { data: project, isLoading } = useProject();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-gray-400 text-sm">
        Loading…
      </div>
    );
  }

  if (!project) return <WelcomeView />;

  return (
    <div className="flex h-screen items-center justify-center text-gray-400 text-sm">
      Project: {project.name} — workspace coming soon
    </div>
  );
}
