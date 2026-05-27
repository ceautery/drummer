import { javascript } from "@codemirror/lang-javascript";
import { EditorState } from "@codemirror/state";
import { oneDark } from "@codemirror/theme-one-dark";
import { basicSetup, EditorView } from "codemirror";
import { useEffect, useRef, useState } from "react";
import { useRequestStore } from "../../store/requestStore";
import { useResponseStore } from "../../store/responseStore";

type ScriptMode = "pre" | "post";

export function ScriptTab() {
  const [mode, setMode] = useState<ScriptMode>("pre");
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  const preScript = useRequestStore(
    (s) =>
      s.draft?.frontmatter.pre_script ?? s.saved?.frontmatter.pre_script ?? "",
  );
  const postScript = useRequestStore(
    (s) =>
      s.draft?.frontmatter.post_script ??
      s.saved?.frontmatter.post_script ??
      "",
  );
  const patch = useRequestStore((s) => s.patch);

  const scriptLogs = useResponseStore((s) => s.scriptLogs);
  const scriptError = useResponseStore((s) => s.scriptError);
  const scriptSuggestion = useResponseStore((s) => s.scriptSuggestion);

  const patchRef = useRef(patch);
  const modeRef = useRef(mode);
  const initialScriptRef = useRef(preScript);

  useEffect(() => {
    patchRef.current = patch;
  }, [patch]);

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  // One-time CodeMirror init
  useEffect(() => {
    if (!editorRef.current) return;
    const view = new EditorView({
      state: EditorState.create({
        doc: initialScriptRef.current,
        extensions: [
          basicSetup,
          javascript(),
          oneDark,
          EditorView.updateListener.of((update) => {
            if (!update.docChanged) return;
            const value = update.state.doc.toString();
            if (modeRef.current === "pre") {
              patchRef.current({ pre_script: value });
            } else {
              patchRef.current({ post_script: value });
            }
          }),
        ],
      }),
      parent: editorRef.current,
    });
    viewRef.current = view;
    return () => view.destroy();
  }, []); // empty dep array: intentional one-time init via refs

  // Sync editor content when mode switches
  const currentScript = mode === "pre" ? preScript : postScript;
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const doc = view.state.doc.toString();
    if (doc !== currentScript) {
      view.dispatch({
        changes: { from: 0, to: view.state.doc.length, insert: currentScript },
      });
    }
  }, [currentScript]);

  const hasOutput = scriptLogs.length > 0 || scriptError !== null;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex shrink-0 gap-1 border-b border-gray-700 px-2 pt-1">
        {(["pre", "post"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className={`rounded-t px-3 py-1 text-xs ${
              mode === m
                ? "bg-gray-700 text-white"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            {m === "pre" ? "Pre-script" : "Post-script"}
          </button>
        ))}
      </div>

      <div ref={editorRef} className="min-h-0 flex-1 overflow-auto" />

      {hasOutput && (
        <div className="max-h-40 shrink-0 overflow-y-auto border-t border-gray-700 bg-gray-900 p-2 font-mono text-xs">
          {scriptLogs.map((log) => (
            <div key={log} className="text-gray-300">
              {log}
            </div>
          ))}
          {scriptError && (
            <div className="mt-1 text-red-400">{scriptError}</div>
          )}
          {scriptSuggestion && (
            <div className="mt-1 text-amber-400">Hint: {scriptSuggestion}</div>
          )}
        </div>
      )}
    </div>
  );
}
