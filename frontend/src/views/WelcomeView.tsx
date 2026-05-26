import { useState } from "react";
import { useSetProject } from "../api/projects";

export function WelcomeView() {
  const [path, setPath] = useState("");
  const { mutate, isPending, error } = useSetProject();

  const handleOpen = () => {
    if (path.trim()) mutate(path.trim());
  };

  return (
    <div
      className="flex h-screen items-center justify-center bg-gray-50"
      data-testid="welcome-card"
    >
      <div className="w-full max-w-md rounded-lg border bg-white p-8 shadow-sm">
        <h1 className="mb-1 text-xl font-semibold">Drummer</h1>
        <p className="mb-6 text-sm text-gray-500">
          Open a project to get started.
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            className="flex-1 rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            placeholder="/path/to/your/project"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleOpen()}
            data-testid="project-path-input"
          />
          <button
            type="button"
            className="rounded bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
            onClick={handleOpen}
            disabled={isPending || !path.trim()}
            data-testid="open-project-button"
          >
            {isPending ? "Opening…" : "Open"}
          </button>
        </div>
        {error && <p className="mt-3 text-sm text-red-600">{error.message}</p>}
      </div>
    </div>
  );
}
