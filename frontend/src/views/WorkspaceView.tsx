import { useCallback, useEffect, useRef } from "react";
import { useRequest, useRequests, useSaveRequest } from "../api/requests";
import { useSend } from "../api/useSend";
import { TwoPanel } from "../components/layout/PanelGroup";
import { Sidebar } from "../components/layout/Sidebar";
import { AuthTab } from "../components/request/AuthTab";
import { BodyTab } from "../components/request/BodyTab";
import { CookiesTab } from "../components/request/CookiesTab";
import { HeadersTab } from "../components/request/HeadersTab";
import { ParamsTab } from "../components/request/ParamsTab";
import { ScriptTab } from "../components/request/ScriptTab";
import { UrlBar } from "../components/request/UrlBar";
import { BodyViewer } from "../components/response/BodyViewer";
import { HeadersViewer } from "../components/response/HeadersViewer";
import { HistoryDrawer } from "../components/response/HistoryDrawer";
import { RawViewer } from "../components/response/RawViewer";
import { ResponseMeta } from "../components/response/ResponseMeta";
import { ScriptOutput } from "../components/response/ScriptOutput";
import { useProjectStore } from "../store/projectStore";
import { useRequestStore } from "../store/requestStore";
import { useResponseStore } from "../store/responseStore";
import { useSessionStore } from "../store/sessionStore";
import type { HttpMethod, RequestTab, ResponseTab } from "../types";

export function WorkspaceView() {
  // ProjectStore selectors
  const project = useProjectStore((s) => s.project);
  const setRequests = useProjectStore((s) => s.setRequests);

  // RequestStore selectors
  const selectedPath = useRequestStore((s) => s.selectedPath);
  const draft = useRequestStore((s) => s.draft);
  const saved = useRequestStore((s) => s.saved);
  const requestTab = useRequestStore((s) => s.activeTab);
  const loadRequest = useRequestStore((s) => s.load);
  const selectRequest = useRequestStore((s) => s.select);
  const patchRequest = useRequestStore((s) => s.patch);
  const discardRequest = useRequestStore((s) => s.discard);
  const markSaved = useRequestStore((s) => s.markSaved);
  const setRequestTab = useRequestStore((s) => s.setTab);
  const isDirty = useRequestStore((s) => s.isDirty);

  // ResponseStore selectors
  const streaming = useResponseStore((s) => s.streaming);
  const statusCode = useResponseStore((s) => s.statusCode);
  const elapsedMs = useResponseStore((s) => s.elapsedMs);
  const body = useResponseStore((s) => s.body);
  const responseHeaders = useResponseStore((s) => s.responseHeaders);
  const responseTab = useResponseStore((s) => s.activeTab);
  const setResponseTab = useResponseStore((s) => s.setTab);

  const { variables } = useSessionStore();

  const { data: requests = [] } = useRequests({
    enabled: project !== null,
  });
  const { data: requestDetail } = useRequest(selectedPath);
  const saveRequest = useSaveRequest();
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

  const current = draft ?? saved;

  const REQUEST_TABS: { id: RequestTab; label: string }[] = [
    { id: "params", label: "Params" },
    { id: "headers", label: "Headers" },
    { id: "body", label: "Body" },
    { id: "auth", label: "Auth" },
    { id: "scripts", label: "Scripts" },
    { id: "cookies", label: "Cookies" },
  ];

  const RESPONSE_TABS: { id: ResponseTab; label: string }[] = [
    { id: "body", label: "Body" },
    { id: "headers", label: "Headers" },
    { id: "raw", label: "Raw" },
    { id: "script-output", label: "Script Output" },
    { id: "history", label: "History" },
  ];

  const contentType =
    responseHeaders.find(([k]) => k.toLowerCase() === "content-type")?.[1] ??
    "";

  const sidebar = <Sidebar onRequestSelect={handleRequestSelect} />;

  const requestPanel = (
    <div className="flex h-full flex-col">
      <UrlBar
        method={current?.frontmatter.method ?? "GET"}
        url={current?.frontmatter.url ?? ""}
        onMethodChange={(m: HttpMethod) => patchRequest({ method: m })}
        onUrlChange={(url) => patchRequest({ url })}
        onSend={handleSend}
        onCancel={cancel}
        isStreaming={streaming === "streaming"}
        variables={variables}
      />
      <div className="flex gap-0 border-b px-2">
        {REQUEST_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setRequestTab(tab.id)}
            className={`px-3 py-1.5 text-xs border-b-2 ${
              requestTab === tab.id
                ? "border-purple-600 text-purple-700"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto">
        {requestTab === "params" && <ParamsTab />}
        {requestTab === "headers" && <HeadersTab />}
        {requestTab === "body" && <BodyTab />}
        {requestTab === "auth" && <AuthTab />}
        {requestTab === "scripts" && <ScriptTab />}
        {requestTab === "cookies" && <CookiesTab />}
      </div>
    </div>
  );

  const responsePanel = (
    <div className="flex h-full flex-col">
      <ResponseMeta
        statusCode={statusCode}
        elapsedMs={elapsedMs}
        bodyLength={body?.length ?? null}
        streaming={streaming}
      />
      <div className="flex gap-0 border-b px-2">
        {RESPONSE_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setResponseTab(tab.id)}
            className={`px-3 py-1.5 text-xs border-b-2 ${
              responseTab === tab.id
                ? "border-purple-600 text-purple-700"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto">
        {responseTab === "body" && (
          <BodyViewer body={body} contentType={contentType} />
        )}
        {responseTab === "headers" && (
          <HeadersViewer headers={responseHeaders} />
        )}
        {responseTab === "raw" && <RawViewer body={body} />}
        {responseTab === "script-output" && <ScriptOutput />}
        {responseTab === "history" && <HistoryDrawer />}
      </div>
    </div>
  );

  const mainArea = (
    <TwoPanel
      left={requestPanel}
      right={responsePanel}
      direction="vertical"
      defaultSizes={[50, 50]}
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
