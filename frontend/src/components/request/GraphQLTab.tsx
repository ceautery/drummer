import { json as jsonLang } from "@codemirror/lang-json";
import { Compartment, EditorState } from "@codemirror/state";
import { graphql as graphqlExtensions, updateSchema } from "cm6-graphql";
import { basicSetup, EditorView } from "codemirror";
import {
  buildClientSchema,
  type GraphQLSchema,
  type IntrospectionQuery,
} from "graphql";
import { useEffect, useRef, useState } from "react";
import { editorThemeExtension } from "../../lib/editorTheme";
import { useRequestStore } from "../../store/requestStore";
import { useResolvedTheme } from "../../store/themeStore";
import type { GraphQLConfig } from "../../types";
import { SchemaExplorer } from "./SchemaExplorer";

type GqlTab = "query" | "variables" | "schema";

function QueryEditor({ schema }: { schema: GraphQLSchema | null }) {
  const { draft, saved, patch } = useRequestStore();
  const current = draft ?? saved;
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const patchRef = useRef(patch);
  const graphqlRef = useRef<GraphQLConfig>(
    current?.frontmatter.graphql ?? { query: "", variables: {} },
  );

  const resolved = useResolvedTheme();
  const themeCompartment = useRef(new Compartment());
  const initialResolvedRef = useRef(resolved);

  useEffect(() => {
    patchRef.current = patch;
  }, [patch]);

  useEffect(() => {
    graphqlRef.current = current?.frontmatter.graphql ?? {
      query: "",
      variables: {},
    };
  }, [current]);

  useEffect(() => {
    if (!editorRef.current) return;
    const view = new EditorView({
      state: EditorState.create({
        doc: graphqlRef.current.query,
        extensions: [
          basicSetup,
          themeCompartment.current.of(
            editorThemeExtension(initialResolvedRef.current),
          ),
          ...graphqlExtensions(),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              const q = update.state.doc.toString();
              patchRef.current({
                graphql: { ...graphqlRef.current, query: q },
              });
            }
          }),
        ],
      }),
      parent: editorRef.current,
    });
    viewRef.current = view;
    return () => view.destroy();
  }, []); // One-time init — uses patchRef and graphqlRef to avoid stale closures

  // Update schema in the editor when it loads
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    updateSchema(view, schema ?? undefined);
  }, [schema]);

  // Sync query from store to editor when current request changes
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const stored = current?.frontmatter.graphql?.query ?? "";
    const cur = view.state.doc.toString();
    if (cur !== stored) {
      view.dispatch({ changes: { from: 0, to: cur.length, insert: stored } });
    }
  }, [current]);

  useEffect(() => {
    viewRef.current?.dispatch({
      effects: themeCompartment.current.reconfigure(
        editorThemeExtension(resolved),
      ),
    });
  }, [resolved]);

  return <div ref={editorRef} className="flex-1 overflow-auto text-sm" />;
}

function VariablesEditor() {
  const { draft, saved, patch } = useRequestStore();
  const current = draft ?? saved;
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const patchRef = useRef(patch);
  const graphqlRef = useRef<GraphQLConfig>(
    current?.frontmatter.graphql ?? { query: "", variables: {} },
  );

  const resolved = useResolvedTheme();
  const themeCompartment = useRef(new Compartment());
  const initialResolvedRef = useRef(resolved);

  useEffect(() => {
    patchRef.current = patch;
  }, [patch]);

  useEffect(() => {
    graphqlRef.current = current?.frontmatter.graphql ?? {
      query: "",
      variables: {},
    };
  }, [current]);

  useEffect(() => {
    if (!editorRef.current) return;
    const view = new EditorView({
      state: EditorState.create({
        doc: JSON.stringify(graphqlRef.current.variables, null, 2),
        extensions: [
          basicSetup,
          themeCompartment.current.of(
            editorThemeExtension(initialResolvedRef.current),
          ),
          jsonLang(),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              const text = update.state.doc.toString();
              try {
                const vars = JSON.parse(text) as Record<string, unknown>;
                patchRef.current({
                  graphql: { ...graphqlRef.current, variables: vars },
                });
              } catch {
                // Skip patch while JSON is invalid mid-edit
              }
            }
          }),
        ],
      }),
      parent: editorRef.current,
    });
    viewRef.current = view;
    return () => view.destroy();
  }, []); // One-time init — uses patchRef and graphqlRef to avoid stale closures

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const stored = JSON.stringify(
      current?.frontmatter.graphql?.variables ?? {},
      null,
      2,
    );
    const cur = view.state.doc.toString();
    if (cur !== stored) {
      view.dispatch({ changes: { from: 0, to: cur.length, insert: stored } });
    }
  }, [current]);

  useEffect(() => {
    viewRef.current?.dispatch({
      effects: themeCompartment.current.reconfigure(
        editorThemeExtension(resolved),
      ),
    });
  }, [resolved]);

  return <div ref={editorRef} className="flex-1 overflow-auto text-sm" />;
}

export function GraphQLTab() {
  const { draft, saved } = useRequestStore();
  const current = draft ?? saved;
  const [activeTab, setActiveTab] = useState<GqlTab>("query");
  const [schema, setSchema] = useState<GraphQLSchema | null>(null);
  const [fetching, setFetching] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const handleFetchSchema = async () => {
    if (!current?.frontmatter.url) return;
    setFetching(true);
    setFetchError(null);
    try {
      const res = await fetch("/api/graphql/introspect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: current.frontmatter.url,
          headers: current.frontmatter.headers,
        }),
      });
      if (res.ok) {
        const data = (await res.json()) as { data: IntrospectionQuery };
        setSchema(buildClientSchema(data.data));
      } else {
        setFetchError("Schema fetch failed");
      }
    } catch {
      setFetchError("Schema fetch failed");
    } finally {
      setFetching(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-1 border-b px-2 py-1">
        {(["query", "variables", "schema"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setActiveTab(t)}
            className={`rounded px-2 py-0.5 text-xs ${
              activeTab === t
                ? "bg-muted text-foreground"
                : "text-muted-foreground hover:bg-muted"
            }`}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {activeTab === "query" && <QueryEditor schema={schema} />}
      {activeTab === "variables" && <VariablesEditor />}
      {activeTab === "schema" && (
        <SchemaExplorer
          schema={schema}
          onFetch={handleFetchSchema}
          fetching={fetching}
          fetchError={fetchError}
        />
      )}
    </div>
  );
}
