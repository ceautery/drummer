import { EditorState } from "@codemirror/state";
import { basicSetup, EditorView } from "codemirror";
import { useEffect, useRef, useState } from "react";
import { useRequestStore } from "../../store/requestStore";
import type { BodyMode } from "../../types";
import { GraphQLTab } from "./GraphQLTab";

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

  // Sync mode when graphql presence changes (e.g. switching requests)
  const hasGraphql = current?.frontmatter.graphql != null;
  useEffect(() => {
    setMode(hasGraphql ? "graphql" : "raw");
  }, [hasGraphql]);

  // Initialize CodeMirror once — editor div is always mounted (hidden when inactive)
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

  const handleModeChange = (newMode: BodyMode) => {
    if (newMode === "graphql" && !current?.frontmatter.graphql) {
      patch({ graphql: { query: "", variables: {} }, method: "POST" });
    }
    setMode(newMode);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex gap-1 border-b px-2 py-1">
        {(["raw", "json", "form-data", "graphql"] as BodyMode[]).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => handleModeChange(m)}
            className={`rounded px-2 py-0.5 text-xs capitalize ${
              mode === m
                ? "bg-purple-100 text-purple-700"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {m === "form-data"
              ? "Form Data"
              : m.charAt(0).toUpperCase() + m.slice(1)}
          </button>
        ))}
      </div>
      {mode === "form-data" && (
        <p className="p-4 text-sm text-gray-400">
          Form-data editor coming soon.
        </p>
      )}
      {mode === "graphql" && <GraphQLTab />}
      {/* Editor div stays mounted; hidden when inactive to preserve CodeMirror state */}
      <div
        ref={editorRef}
        className={`flex-1 overflow-auto text-sm ${
          mode === "raw" || mode === "json" ? "" : "hidden"
        }`}
      />
    </div>
  );
}
