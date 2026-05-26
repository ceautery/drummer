import { RangeSetBuilder } from "@codemirror/state";
import {
  Decoration,
  type DecorationSet,
  type EditorView,
  ViewPlugin,
  type ViewUpdate,
} from "@codemirror/view";

const VAR_REGEX = /\{\{([^}]+)\}\}/g;

function buildDecorations(
  view: EditorView,
  variables: Record<string, string>,
): DecorationSet {
  const builder = new RangeSetBuilder<Decoration>();
  for (const { from, to } of view.visibleRanges) {
    const text = view.state.sliceDoc(from, to);
    VAR_REGEX.lastIndex = 0;
    let match = VAR_REGEX.exec(text);
    while (match !== null) {
      const varName = match[1] ?? "";
      const start = from + match.index;
      const end = start + match[0].length;
      const isKnown = varName in variables;
      builder.add(
        start,
        end,
        Decoration.mark({
          class: isKnown ? "cm-var-known" : "cm-var-unknown",
          attributes: {
            title: isKnown ? (variables[varName] ?? "") : "Not set",
          },
        }),
      );
      match = VAR_REGEX.exec(text);
    }
  }
  return builder.finish();
}

export function variableHighlighter(variables: Record<string, string>) {
  return ViewPlugin.fromClass(
    class {
      decorations: DecorationSet;
      constructor(view: EditorView) {
        this.decorations = buildDecorations(view, variables);
      }
      update(update: ViewUpdate) {
        if (update.docChanged || update.viewportChanged) {
          this.decorations = buildDecorations(update.view, variables);
        }
      }
    },
    { decorations: (v) => v.decorations },
  );
}
