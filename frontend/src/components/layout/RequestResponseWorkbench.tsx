import { useRequestStore } from "../../store/requestStore";
import { useResponseStore } from "../../store/responseStore";
import { useSessionStore } from "../../store/sessionStore";
import type { HttpMethod, RequestTab, ResponseTab } from "../../types";
import { AuthTab } from "../request/AuthTab";
import { BodyTab } from "../request/BodyTab";
import { CookiesTab } from "../request/CookiesTab";
import { HeadersTab } from "../request/HeadersTab";
import { ParamsTab } from "../request/ParamsTab";
import { ScriptTab } from "../request/ScriptTab";
import { UrlBar } from "../request/UrlBar";
import { BodyViewer } from "../response/BodyViewer";
import { HeadersViewer } from "../response/HeadersViewer";
import { HistoryDrawer } from "../response/HistoryDrawer";
import { RawViewer } from "../response/RawViewer";
import { ResponseMeta } from "../response/ResponseMeta";
import { ScriptOutput } from "../response/ScriptOutput";
import { TwoPanel } from "./PanelGroup";

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

interface RequestResponseWorkbenchProps {
  onSend: () => void;
  onCancel: () => void;
}

export function RequestResponseWorkbench({
  onSend,
  onCancel,
}: RequestResponseWorkbenchProps) {
  const saved = useRequestStore((s) => s.saved);
  const draft = useRequestStore((s) => s.draft);
  const patchRequest = useRequestStore((s) => s.patch);
  const requestTab = useRequestStore((s) => s.activeTab);
  const setRequestTab = useRequestStore((s) => s.setTab);

  const streaming = useResponseStore((s) => s.streaming);
  const statusCode = useResponseStore((s) => s.statusCode);
  const elapsedMs = useResponseStore((s) => s.elapsedMs);
  const body = useResponseStore((s) => s.body);
  const responseHeaders = useResponseStore((s) => s.responseHeaders);
  const responseTab = useResponseStore((s) => s.activeTab);
  const setResponseTab = useResponseStore((s) => s.setTab);

  const { variables } = useSessionStore();

  const current = draft ?? saved;
  const contentType =
    responseHeaders.find(([k]) => k.toLowerCase() === "content-type")?.[1] ??
    "";

  const requestPanel = (
    <div className="flex h-full flex-col">
      <UrlBar
        method={current?.frontmatter.method ?? "GET"}
        url={current?.frontmatter.url ?? ""}
        onMethodChange={(m: HttpMethod) => patchRequest({ method: m })}
        onUrlChange={(url) => patchRequest({ url })}
        onSend={onSend}
        onCancel={onCancel}
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
                ? "border-primary text-primary"
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
                ? "border-primary text-primary"
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

  return (
    <TwoPanel
      left={requestPanel}
      right={responsePanel}
      direction="vertical"
      defaultSizes={[50, 50]}
    />
  );
}
