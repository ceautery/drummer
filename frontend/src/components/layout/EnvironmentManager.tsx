import { useEffect, useState } from "react";
import {
  useCreateEnvironment,
  useDeleteEnvironment,
  useEnvironment,
  useEnvironments,
  useSaveEnvironment,
} from "../../api/environments";
import { useSessionStore } from "../../store/sessionStore";
import { KeyValueTable } from "../request/KeyValueTable";
import { Dialog, DialogPopup, DialogTitle } from "../ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";

interface EnvironmentManagerProps {
  open: boolean;
  onClose: () => void;
}

export function EnvironmentManager({ open, onClose }: EnvironmentManagerProps) {
  const { data: environments = [] } = useEnvironments();
  const activeEnvironment = useSessionStore((s) => s.activeEnvironment);
  const setActiveEnvironment = useSessionStore((s) => s.setActiveEnvironment);

  const createEnv = useCreateEnvironment();
  const deleteEnv = useDeleteEnvironment();
  const saveEnv = useSaveEnvironment();

  const [editingName, setEditingName] = useState<string>("");
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const { data: detail } = useEnvironment(editingName || null);

  useEffect(() => {
    if (!open) return;
    const names = environments.map((e) => e.name);
    setError(null);
    setEditingName((prev) => {
      if (prev && names.includes(prev)) return prev;
      if (names.includes(activeEnvironment)) return activeEnvironment;
      return names[0] ?? "";
    });
  }, [open, environments, activeEnvironment]);

  useEffect(() => {
    if (detail) setDraft(detail.variables);
  }, [detail]);

  const isDirty =
    detail !== undefined &&
    JSON.stringify(draft) !== JSON.stringify(detail.variables);

  const switchEnv = (next: string) => {
    if (isDirty && !window.confirm("Discard unsaved variable changes?")) return;
    setError(null);
    setEditingName(next);
  };

  const handleSave = () => {
    if (!editingName) return;
    saveEnv.mutate({ name: editingName, variables: draft });
  };

  const handleNew = () => {
    const name = window.prompt("New environment name:")?.trim();
    if (!name) return;
    if (environments.some((e) => e.name === name)) {
      setError(`An environment named '${name}' already exists`);
      return;
    }
    createEnv.mutate(
      { name, variables: {} },
      {
        onSuccess: () => {
          setError(null);
          setEditingName(name);
        },
        onError: () => setError(`Could not create '${name}'`),
      },
    );
  };

  const handleDelete = () => {
    if (!editingName) return;
    if (
      !window.confirm(
        `Delete environment '${editingName}'? This cannot be undone.`,
      )
    )
      return;
    const deleted = editingName;
    deleteEnv.mutate(deleted, {
      onSuccess: () => {
        const remaining = environments
          .map((e) => e.name)
          .filter((n) => n !== deleted);
        if (activeEnvironment === deleted) {
          setActiveEnvironment(remaining[0] ?? "local");
        }
        setEditingName(remaining[0] ?? "");
      },
    });
  };

  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) onClose();
  };

  const handleSelectChange = (v: string | null) => {
    if (v) switchEnv(v);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogPopup className="flex flex-col gap-3">
        <DialogTitle>Manage Environments</DialogTitle>

        <div className="flex items-center gap-2">
          <Select value={editingName} onValueChange={handleSelectChange}>
            <SelectTrigger size="sm" className="min-w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {environments.map((e) => (
                <SelectItem key={e.name} value={e.name}>
                  {e.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <button
            type="button"
            className="rounded border px-2 py-1 text-xs hover:bg-muted"
            onClick={handleNew}
            data-testid="env-new-button"
          >
            + New
          </button>
          <button
            type="button"
            className="rounded border px-2 py-1 text-xs text-destructive hover:bg-muted disabled:opacity-40"
            onClick={handleDelete}
            disabled={!editingName}
            data-testid="env-delete-button"
          >
            Delete
          </button>
        </div>

        {error && (
          <p className="text-xs text-destructive" role="alert">
            {error}
          </p>
        )}

        {editingName ? (
          <KeyValueTable
            entries={draft}
            onChange={setDraft}
            keyPlaceholder="Variable"
            valuePlaceholder="Value"
          />
        ) : (
          <p className="px-2 py-4 text-xs text-muted-foreground">
            No environment selected. Create one with the "+ New" button.
          </p>
        )}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            className="rounded border px-3 py-1.5 text-sm hover:bg-muted"
            onClick={onClose}
          >
            Close
          </button>
          <button
            type="button"
            className="rounded bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-40"
            onClick={handleSave}
            disabled={!editingName || !isDirty}
            data-testid="env-save-button"
          >
            Save
          </button>
        </div>
      </DialogPopup>
    </Dialog>
  );
}
