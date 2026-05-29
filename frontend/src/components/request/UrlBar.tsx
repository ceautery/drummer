import { Compartment, EditorState } from "@codemirror/state";
import { basicSetup, EditorView } from "codemirror";
import { useEffect, useRef } from "react";
import { variableHighlighter } from "../../lib/codemirror-variables";
import { editorThemeExtension } from "../../lib/editorTheme";
import { useResolvedTheme } from "../../store/themeStore";
import type { HttpMethod } from "../../types";

const METHODS: HttpMethod[] = [
  "GET",
  "POST",
  "PUT",
  "PATCH",
  "DELETE",
  "HEAD",
  "OPTIONS",
];

const METHOD_COLOUR: Record<HttpMethod, string> = {
  GET: "text-green-700 dark:text-green-400",
  POST: "text-blue-700 dark:text-blue-400",
  PUT: "text-amber-700 dark:text-amber-400",
  PATCH: "text-orange-600 dark:text-orange-400",
  DELETE: "text-red-700 dark:text-red-400",
  HEAD: "text-muted-foreground",
  OPTIONS: "text-muted-foreground",
  TRACE: "text-muted-foreground",
};

interface UrlBarProps {
  method: HttpMethod;
  url: string;
  onMethodChange: (method: HttpMethod) => void;
  onUrlChange: (url: string) => void;
  onSend: () => void;
  onCancel: () => void;
  isStreaming: boolean;
  variables: Record<string, string>;
}

export function UrlBar({
  method,
  url,
  onMethodChange,
  onUrlChange,
  onSend,
  onCancel,
  isStreaming,
  variables,
}: UrlBarProps) {
  const resolved = useResolvedTheme();
  const themeCompartment = useRef(new Compartment());
  const initialResolvedRef = useRef(resolved);

  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const onSendRef = useRef(onSend);
  const onUrlChangeRef = useRef(onUrlChange);
  const isStreamingRef = useRef(isStreaming);
  const variablesRef = useRef(variables);

  // Keep refs in sync with latest props to avoid stale closures
  useEffect(() => {
    onSendRef.current = onSend;
  }, [onSend]);
  useEffect(() => {
    onUrlChangeRef.current = onUrlChange;
  }, [onUrlChange]);
  useEffect(() => {
    isStreamingRef.current = isStreaming;
  }, [isStreaming]);
  useEffect(() => {
    variablesRef.current = variables;
  }, [variables]);

  // Initialize CodeMirror once
  useEffect(() => {
    if (!editorRef.current) return;

    const view = new EditorView({
      state: EditorState.create({
        doc: "",
        extensions: [
          basicSetup,
          themeCompartment.current.of(
            editorThemeExtension(initialResolvedRef.current),
          ),
          EditorView.lineWrapping,
          variableHighlighter(variablesRef.current),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              onUrlChangeRef.current(update.state.doc.toString());
            }
          }),
          EditorView.domEventHandlers({
            keydown: (e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                if (!isStreamingRef.current) onSendRef.current();
              }
            },
          }),
          EditorView.theme({
            "&": { fontSize: "0.875rem", fontFamily: "inherit" },
            ".cm-content": { padding: "4px 8px", minHeight: "32px" },
            ".cm-focused": { outline: "none" },
            ".cm-scroller": { overflow: "hidden" },
          }),
        ],
      }),
      parent: editorRef.current,
    });

    viewRef.current = view;
    return () => view.destroy();
  }, []); // One-time init: uses refs instead of captured closures

  // Sync url prop to editor
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const current = view.state.doc.toString();
    if (current !== url) {
      view.dispatch({ changes: { from: 0, to: current.length, insert: url } });
    }
  }, [url]);

  useEffect(() => {
    viewRef.current?.dispatch({
      effects: themeCompartment.current.reconfigure(
        editorThemeExtension(resolved),
      ),
    });
  }, [resolved]);

  return (
    <div className="flex items-stretch gap-2 border-b px-3 py-2">
      <select
        className={`rounded border px-2 text-sm font-mono font-semibold ${METHOD_COLOUR[method]}`}
        value={method}
        onChange={(e) => onMethodChange(e.target.value as HttpMethod)}
      >
        {METHODS.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>

      <div
        ref={editorRef}
        className="cm-url-bar flex-1 rounded border focus-within:ring-2 focus-within:ring-primary"
        data-testid="url-input"
      />

      {isStreaming ? (
        <button
          type="button"
          className="rounded bg-muted px-4 py-1.5 text-sm font-medium hover:bg-muted/80"
          onClick={onCancel}
        >
          Cancel
        </button>
      ) : (
        <button
          type="button"
          className="rounded bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          onClick={onSend}
          data-testid="send-button"
        >
          Send
        </button>
      )}
    </div>
  );
}
