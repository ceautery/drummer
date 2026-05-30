import { useCallback, useEffect, useRef } from "react";
import {
  useCreateRequest,
  useDeleteRequest,
  useRequest,
  useRequests,
  useSaveRequest,
} from "../api/requests";
import { useSend } from "../api/useSend";
import { TwoPanel } from "../components/layout/PanelGroup";
import { RequestResponseWorkbench } from "../components/layout/RequestResponseWorkbench";
import { Sidebar } from "../components/layout/Sidebar";
import { useProjectStore } from "../store/projectStore";
import { useRequestStore } from "../store/requestStore";

export function WorkspaceView() {
  // ProjectStore selectors
  const project = useProjectStore((s) => s.project);
  const setRequests = useProjectStore((s) => s.setRequests);

  // RequestStore selectors
  const selectedPath = useRequestStore((s) => s.selectedPath);
  const draft = useRequestStore((s) => s.draft);
  const saved = useRequestStore((s) => s.saved);
  const loadRequest = useRequestStore((s) => s.load);
  const selectRequest = useRequestStore((s) => s.select);
  const discardRequest = useRequestStore((s) => s.discard);
  const markSaved = useRequestStore((s) => s.markSaved);
  const isDirty = useRequestStore((s) => s.isDirty);
  const deselect = useRequestStore((s) => s.deselect);

  const { data: requests = [] } = useRequests({
    enabled: project !== null,
  });
  const { data: requestDetail } = useRequest(selectedPath);
  const saveRequest = useSaveRequest();
  const createRequest = useCreateRequest();
  const deleteRequest = useDeleteRequest();
  const { send, cancel } = useSend();

  // Load request into store when data arrives
  useEffect(() => {
    if (requestDetail) loadRequest(requestDetail);
  }, [requestDetail, loadRequest]);

  // Sync request list into projectStore
  useEffect(() => {
    setRequests(requests);
  }, [requests, setRequests]);

  const handleRequestSelect = useCallback(
    (path: string) => {
      if (selectedPath !== path && isDirty()) {
        if (!window.confirm("You have unsaved changes. Discard them?")) return;
        discardRequest();
      }
      selectRequest(path);
    },
    [selectedPath, isDirty, discardRequest, selectRequest],
  );

  const handleSend = useCallback(() => {
    if (selectedPath) void send(selectedPath);
  }, [selectedPath, send]);

  const handleSave = useCallback(async () => {
    if (!selectedPath || (!draft && !saved)) return;
    const detail = draft ?? saved;
    if (!detail) return;
    const result = await saveRequest.mutateAsync({
      path: selectedPath,
      detail,
    });
    markSaved(result);
  }, [selectedPath, draft, saved, saveRequest, markSaved]);

  const handleNewRequest = useCallback(async () => {
    const name = window.prompt("New request name:")?.trim();
    if (!name) return;
    const slug =
      name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/(^-|-$)/g, "") || "request";
    const path = `${slug}.md`;
    await createRequest.mutateAsync({ path, name });
    handleRequestSelect(path);
  }, [createRequest, handleRequestSelect]);

  const handleRequestDelete = useCallback(
    async (path: string) => {
      if (!window.confirm("Delete this request? This cannot be undone."))
        return;
      await deleteRequest.mutateAsync(path);
      if (selectedPath === path) deselect();
    },
    [deleteRequest, selectedPath, deselect],
  );

  const handleSaveRef = useRef(handleSave);
  useEffect(() => {
    handleSaveRef.current = handleSave;
  }, [handleSave]);

  // Cmd+S / Ctrl+S save
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        void handleSaveRef.current();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const sidebar = (
    <Sidebar
      onRequestSelect={handleRequestSelect}
      onRequestDelete={handleRequestDelete}
      onNewRequest={handleNewRequest}
    />
  );

  const mainArea = (
    <RequestResponseWorkbench
      onSend={handleSend}
      onCancel={cancel}
      onSave={handleSave}
    />
  );

  return (
    <div className="flex h-full">
      <TwoPanel
        left={sidebar}
        right={mainArea}
        direction="horizontal"
        defaultSizes={[20, 80]}
      />
    </div>
  );
}
