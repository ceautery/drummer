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
  const projectStore = useProjectStore();
  const requestStore = useRequestStore();
  const responseStore = useResponseStore();
  const { variables } = useSessionStore();

  const { data: requests = [] } = useRequests({
    enabled: projectStore.project !== null,
  });
  const { data: requestDetail } = useRequest(requestStore.selectedPath);
  const saveRequest = useSaveRequest();
  const { send, cancel } = useSend();

  // Load request into store when data arrives
  useEffect(() => {
    if (requestDetail) requestStore.load(requestDetail);
  }, [requestDetail, requestStore]);

  // Sync request list into projectStore
  useEffect(() => {
    projectStore.setRequests(requests);
  }, [requests, projectStore]);

  const handleRequestSelect = useCallback(
    (path: string) => {
      requestStore.select(path);
    },
    [requestStore],
  );

  const handleSend = useCallback(() => {
    if (requestStore.selectedPath) void send(requestStore.selectedPath);
  }, [requestStore.selectedPath, send]);

  const handleSave = useCallback(async () => {
    const { selectedPath, draft, saved, markSaved } = requestStore;
    if (!selectedPath || (!draft && !saved)) return;
    const detail = draft ?? saved;
    if (!detail) return;
    const result = await saveRequest.mutateAsync({
      path: selectedPath,
      detail,
    });
    markSaved(result);
  }, [requestStore, saveRequest]);

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

  const current = requestStore.draft ?? requestStore.saved;
  const requestTab = requestStore.activeTab;
  const responseTab = responseStore.activeTab;

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
    responseStore.responseHeaders.find(
      ([k]) => k.toLowerCase() === "content-type",
    )?.[1] ?? "";

  const sidebar = <Sidebar onRequestSelect={handleRequestSelect} />;

  const requestPanel = (
    <div className="flex h-full flex-col">
      <UrlBar
        method={current?.frontmatter.method ?? "GET"}
        url={current?.frontmatter.url ?? ""}
        onMethodChange={(m: HttpMethod) => requestStore.patch({ method: m })}
        onUrlChange={(url) => requestStore.patch({ url })}
        onSend={handleSend}
        onCancel={cancel}
        isStreaming={responseStore.streaming === "streaming"}
        variables={variables}
      />
      <div className="flex gap-0 border-b px-2">
        {REQUEST_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => requestStore.setTab(tab.id)}
            className={`px-3 py-1.5 text-xs border-b-2 ${
              requestTab === tab.id
                ? "border-purple-600 text-purple-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
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
        statusCode={responseStore.statusCode}
        elapsedMs={responseStore.elapsedMs}
        bodyLength={responseStore.body?.length ?? null}
        streaming={responseStore.streaming}
      />
      <div className="flex gap-0 border-b px-2">
        {RESPONSE_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => responseStore.setTab(tab.id)}
            className={`px-3 py-1.5 text-xs border-b-2 ${
              responseTab === tab.id
                ? "border-purple-600 text-purple-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto">
        {responseTab === "body" && (
          <BodyViewer body={responseStore.body} contentType={contentType} />
        )}
        {responseTab === "headers" && (
          <HeadersViewer headers={responseStore.responseHeaders} />
        )}
        {responseTab === "raw" && <RawViewer body={responseStore.body} />}
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
    <div className="flex h-screen">
      <TwoPanel
        left={sidebar}
        right={mainArea}
        direction="horizontal"
        defaultSizes={[20, 80]}
      />
    </div>
  );
}
