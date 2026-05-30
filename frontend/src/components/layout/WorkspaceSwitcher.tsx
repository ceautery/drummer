import type * as React from "react";
import { useMemo } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useCreateWorkspace,
  useForgetWorkspace,
  useRegisterWorkspace,
  useSwitchWorkspace,
  useWorkspaces,
} from "../../api/workspaces";
import { useRequestStore } from "../../store/requestStore";
import type { WorkspaceInfo } from "../../types";

const NEW = "__new__";
const ADD = "__add__";
const FORGET = "__forget__";

export function WorkspaceSwitcher() {
  const { data } = useWorkspaces();
  const switchWorkspace = useSwitchWorkspace();
  const createWorkspace = useCreateWorkspace();
  const registerWorkspace = useRegisterWorkspace();
  const forgetWorkspace = useForgetWorkspace();
  const isDirty = useRequestStore((s) => s.isDirty);
  const discard = useRequestStore((s) => s.discard);

  const active = data?.active ?? "scratch";
  const workspaces = data?.workspaces ?? [];
  const activeIsExternal =
    workspaces.find((w) => w.id === active)?.kind === "external";

  const guarded = (run: () => void) => {
    if (isDirty()) {
      if (!window.confirm("You have unsaved changes. Discard them?")) return;
      discard();
    }
    run();
  };

  const switchTo = (info: WorkspaceInfo) => switchWorkspace.mutate(info.id);

  const handleChange = (value: string | null) => {
    if (value === null) return;
    if (value === NEW) {
      const name = window.prompt("New workspace name:")?.trim();
      if (name) {
        guarded(() => createWorkspace.mutate(name, { onSuccess: switchTo }));
      }
      return;
    }
    if (value === ADD) {
      const path = window.prompt("Path to existing project folder:")?.trim();
      if (path) {
        guarded(() => registerWorkspace.mutate(path, { onSuccess: switchTo }));
      }
      return;
    }
    if (value === FORGET) {
      if (
        window.confirm("Forget this external workspace? Files are not deleted.")
      ) {
        forgetWorkspace.mutate(active);
      }
      return;
    }
    if (value !== active) guarded(() => switchWorkspace.mutate(value));
  };

  const itemLabels = useMemo<Record<string, React.ReactNode>>(
    // Sentinel action items (NEW/ADD) are intentionally omitted here, so the trigger
    // label only ever resolves to a real workspace name — never "+ New workspace…".
    () => Object.fromEntries(workspaces.map((w) => [w.id, w.name] as const)),
    [workspaces],
  );

  return (
    <Select value={active} onValueChange={handleChange} items={itemLabels}>
      <SelectTrigger size="sm" className="min-w-44">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {workspaces.map((w) => (
          <SelectItem key={w.id} value={w.id}>
            <span className="flex items-center gap-1.5">
              {w.is_scratch && <span>⌂</span>}
              {w.name}
              {w.kind === "external" && (
                <span className="rounded bg-muted px-1 text-[10px] text-muted-foreground">
                  external
                </span>
              )}
            </span>
          </SelectItem>
        ))}
        <SelectSeparator />
        <SelectItem value={NEW}>+ New workspace…</SelectItem>
        <SelectItem value={ADD}>⊕ Add existing folder…</SelectItem>
        {activeIsExternal && (
          <SelectItem value={FORGET}>✕ Forget external workspace…</SelectItem>
        )}
      </SelectContent>
    </Select>
  );
}
