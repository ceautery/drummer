import { EditorState } from "@codemirror/state";
import { basicSetup, EditorView } from "codemirror";
import { useEffect, useRef, useState } from "react";
import { useRequestStore } from "../../store/requestStore";

type BodyMode = "raw" | "json" | "form-data" | "graphql";

export function BodyTab() {
  const { saved, draft, patch } = useRequestStore();
  const current = draft ?? saved;
  const body = current?.body ?? "";
  const [mode, setMode] = useState<BodyMode>("raw");

  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const patchRef = useRef(patch);

  useEffect(() => {
    patchRef.current = patch;
  }, [patch]);

  // Initialize CodeMirror once
  useEffect(() => {
    if (!editorRef.current) return;
    const view = new EditorView({
      state: EditorState.create({
        doc: "",
        extensions: [
          basicSetup,
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              patchRef.current({ body: update.state.doc.toString() });
            }
          }),
        ],
      }),
      parent: editorRef.current,
    });
    viewRef.current = view;
    return () => view.destroy();
  }, []); // One-time init — uses patchRef to avoid stale closure

  // Sync body prop to editor
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const cur = view.state.doc.toString();
    if (cur !== body) {
      view.dispatch({ changes: { from: 0, to: cur.length, insert: body } });
    }
  }, [body]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex gap-1 border-b px-2 py-1">
        {(["raw", "json", "form-data", "graphql"] as BodyMode[]).map((m) => (
          <button
            key={m}
            type="button"
            disabled={m === "graphql"}
            onClick={() => setMode(m)}
            className={`rounded px-2 py-0.5 text-xs capitalize ${
              m === "graphql"
                ? "cursor-not-allowed text-gray-300"
                : mode === m
                  ? "bg-purple-100 text-purple-700"
                  : "text-gray-600 hover:bg-gray-100"
            }`}
            title={
              m === "graphql" ? "Available in Phase 8 (GraphQL)" : undefined
            }
          >
            {m === "form-data"
              ? "Form Data"
              : m.charAt(0).toUpperCase() + m.slice(1)}
          </button>
        ))}
      </div>
      {mode === "form-data" ? (
        <p className="p-4 text-sm text-gray-400">
          Form-data editor coming soon.
        </p>
      ) : (
        <div ref={editorRef} className="flex-1 overflow-auto text-sm" />
      )}
    </div>
  );
}
