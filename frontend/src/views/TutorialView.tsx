import { useState } from "react";
import { ThemeToggle } from "../components/layout/ThemeToggle";
import { BodyViewer } from "../components/response/BodyViewer";
import { ResponseMeta } from "../components/response/ResponseMeta";
import { ScriptOutputView } from "../components/response/ScriptOutput";
import { useViewStore } from "../store/viewStore";
import type { StreamingState } from "../types";

interface StepMeta {
  title: string;
  instructions: string;
  hasRequest: boolean;
  displayMethod: string;
  displayUrl: string;
}

const STEPS: StepMeta[] = [
  {
    title: "Welcome to Drummer",
    instructions:
      "Welcome to Drummer!\n\nThis tutorial walks you through the core features using a sample of the Metropolitan Museum of Art's collection.\n\nYou'll learn:\n  • How to send HTTP GET requests\n  • How to use path and query parameters\n  • How to manage environment variables\n  • How to run pre- and post-request scripts\n\nThe mock Met API is built into Drummer — no internet connection required.\n\nClick Next to send your first request.",
    hasRequest: false,
    displayMethod: "",
    displayUrl: "",
  },
  {
    title: "Your first GET request",
    instructions:
      "The simplest HTTP request is a GET with no parameters. It retrieves a resource — the response format depends on the endpoint, though JSON is a common choice for APIs.\n\nThis request fetches all museum departments — five major collection areas used to organize the Met's 1.5 million objects.\n\nClick Send to try it. The response appears on the right.",
    hasRequest: true,
    displayMethod: "GET",
    displayUrl: "http://localhost:8000/mock/met/departments",
  },
  {
    title: "Path parameters",
    instructions:
      "REST APIs use path parameters to identify a specific resource. Instead of listing all objects, you can fetch one by its ID.\n\nObject 436532 is Van Gogh's Self-Portrait with a Straw Hat (1887). The ID is embedded directly in the URL path.\n\nClick Send to retrieve it.",
    hasRequest: true,
    displayMethod: "GET",
    displayUrl: "http://localhost:8000/mock/met/objects/436532",
  },
  {
    title: "Query parameters",
    instructions:
      "Query parameters (after the ?) filter or refine a request without changing the path.\n\nThe search endpoint accepts ?q= to search across title, artist, and medium. After sending, try changing 'sunflowers' to another term.\n\nClick Send to search.",
    hasRequest: true,
    displayMethod: "GET",
    displayUrl: "http://localhost:8000/mock/met/search?q=sunflowers",
  },
  {
    title: "Environment variables",
    instructions:
      "Hardcoding http://localhost:8000 in every URL is brittle. Environment variables let you define base_url once and reuse it.\n\nNotice the URL uses {{base_url}}. Drummer substitutes the variable value before sending. The 'local' environment defines base_url=http://localhost:8000.\n\nClick Send to see variable substitution in action.",
    hasRequest: true,
    displayMethod: "GET",
    displayUrl: "{{base_url}}/mock/met/departments",
  },
  {
    title: "Pre-request scripts",
    instructions:
      'Pre-request scripts run JavaScript before the HTTP call. They can read and modify the outgoing request.\n\nThis script sets a custom header using dm.request:\n\n  dm.request.headers["X-Tutorial-Id"] = "drummer-tutorial-step-6";\n  dm.console.log("Header set:", dm.request.headers["X-Tutorial-Id"]);\n\nThe dm.console.log output appears in the script output panel below the response.\n\nClick Send to run it.',
    hasRequest: true,
    displayMethod: "GET",
    displayUrl: "http://localhost:8000/mock/met/objects/436532",
  },
  {
    title: "Post-request scripts",
    instructions:
      'Post-request scripts run JavaScript after the HTTP call. They can read the response and extract data.\n\nThis script reads the JSON response and logs the artwork\'s details:\n\n  var obj = dm.response.json();\n  dm.console.log("Title:", obj.title);\n  dm.console.log("Artist:", obj.artistDisplayName);\n\nUse dm.env.set("key", value) to store response data as variables for use in later requests.\n\nClick Send to run it.',
    hasRequest: true,
    displayMethod: "GET",
    displayUrl: "http://localhost:8000/mock/met/objects/436532",
  },
];

interface TutorialResponseState {
  statusCode: number | null;
  body: string | null;
  elapsedMs: number | null;
  scriptLogs: string[];
  scriptError: string | null;
  scriptSuggestion: string | null;
  error: string | null;
}

export function TutorialView() {
  const setView = useViewStore((s) => s.setView);
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [response, setResponse] = useState<TutorialResponseState | null>(null);
  const [sending, setSending] = useState(false);

  const step = STEPS[currentStep];
  if (!step) return null;

  const handleSend = async () => {
    setSending(true);
    setResponse(null);

    const res = await fetch(`/api/tutorial/steps/${currentStep}/send`, {
      method: "POST",
    });

    if (!res.ok || !res.body) {
      setResponse({
        statusCode: null,
        body: null,
        elapsedMs: null,
        scriptLogs: [],
        scriptError: `HTTP ${res.status}`,
        scriptSuggestion: null,
        error: null,
      });
      setSending(false);
      return;
    }

    const partial: TutorialResponseState = {
      statusCode: null,
      body: null,
      elapsedMs: null,
      scriptLogs: [],
      scriptError: null,
      scriptSuggestion: null,
      error: null,
    };

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let event = "";
    let done = false;

    try {
      while (!done) {
        const chunk = await reader.read();
        done = chunk.done;
        if (chunk.value) {
          buffer += decoder.decode(chunk.value, { stream: true });
        }
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (line.startsWith("event:")) {
            event = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            const data = JSON.parse(line.slice(5).trim()) as Record<
              string,
              unknown
            >;
            if (event === "status") {
              partial.statusCode = data.status_code as number;
            } else if (event === "body") {
              partial.body = data.body as string;
              partial.elapsedMs = data.elapsed_ms as number;
            } else if (event === "done") {
              partial.scriptLogs = (data.script_logs as string[]) ?? [];
              partial.scriptError =
                (data.script_error as string | null) ?? null;
              partial.scriptSuggestion =
                (data.script_suggestion as string | null) ?? null;
            } else if (event === "error") {
              partial.error = data.message as string;
            }
            setResponse({ ...partial });
          }
        }
      }
    } catch {
      setResponse({ ...partial, error: "Connection lost" });
    } finally {
      setSending(false);
    }
  };

  const handleNext = () => {
    setCompletedSteps((prev) => new Set(prev).add(currentStep));
    setResponse(null);
    setCurrentStep((prev) => Math.min(prev + 1, STEPS.length - 1));
  };

  const handleBack = () => {
    setResponse(null);
    setCurrentStep((prev) => Math.max(prev - 1, 0));
  };

  const navigateToStep = (i: number) => {
    setResponse(null);
    setCurrentStep(i);
  };

  const streaming: StreamingState = sending
    ? "streaming"
    : response?.error
      ? "error"
      : response
        ? "done"
        : "idle";

  const hasScriptOutput =
    response !== null &&
    (response.scriptLogs.length > 0 || response.scriptError !== null);

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      {/* Nav bar */}
      <nav className="flex shrink-0 items-center gap-4 border-b bg-card px-4 py-2">
        <span className="text-sm font-semibold text-foreground">
          🥁 Drummer
        </span>
        <div className="flex gap-1">
          <button
            type="button"
            onClick={() => setView("workspace")}
            className="rounded px-3 py-1 text-xs text-muted-foreground hover:text-foreground"
          >
            Workspace
          </button>
          <button
            type="button"
            className="rounded bg-primary/10 px-3 py-1 text-xs text-primary"
          >
            Tutorial
          </button>
        </div>
        <div className="ml-auto">
          <ThemeToggle />
        </div>
      </nav>

      {/* Two-column body */}
      <div className="flex min-h-0 flex-1 overflow-hidden">
        {/* Left column */}
        <div className="flex w-72 shrink-0 flex-col border-r bg-card p-4">
          {/* Step list */}
          <div className="mb-4">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Progress
            </div>
            <div className="flex flex-col gap-1">
              {STEPS.map((s, i) => (
                <button
                  key={s.title}
                  type="button"
                  onClick={() => navigateToStep(i)}
                  className={`flex items-center gap-2 rounded px-2 py-1.5 text-left text-xs ${
                    i === currentStep
                      ? "border border-primary bg-primary/10 text-primary"
                      : completedSteps.has(i)
                        ? "bg-green-500/10 text-green-700 dark:text-green-400"
                        : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <span className="w-4 shrink-0 text-center">
                    {completedSteps.has(i)
                      ? "✓"
                      : i === currentStep
                        ? "▶"
                        : "○"}
                  </span>
                  {s.title}
                </button>
              ))}
            </div>
          </div>

          {/* Instructions */}
          <div className="mb-4 min-h-0 flex-1 overflow-y-auto">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Instructions
            </div>
            <div className="whitespace-pre-wrap text-xs leading-relaxed text-muted-foreground">
              {step.instructions}
            </div>
          </div>

          {/* Back / Next */}
          <div className="flex gap-2 border-t pt-3">
            <button
              type="button"
              onClick={handleBack}
              disabled={currentStep === 0}
              className="rounded bg-muted px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground disabled:opacity-30"
            >
              ← Back
            </button>
            <button
              type="button"
              onClick={handleNext}
              disabled={currentStep === STEPS.length - 1}
              className="flex-1 rounded bg-primary px-3 py-1.5 text-xs text-primary-foreground hover:bg-primary/90 disabled:opacity-30"
            >
              Next →
            </button>
          </div>
        </div>

        {/* Right column */}
        <div className="flex flex-1 flex-col overflow-hidden p-4">
          {step.hasRequest ? (
            <>
              {/* Request card */}
              <div className="mb-4 shrink-0">
                <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Request
                </div>
                <div className="flex items-center gap-2 rounded bg-muted px-3 py-2">
                  <span className="rounded bg-primary/15 px-2 py-0.5 text-xs font-semibold text-primary">
                    {step.displayMethod}
                  </span>
                  <span className="flex-1 truncate font-mono text-xs text-foreground">
                    {step.displayUrl}
                  </span>
                  <button
                    type="button"
                    onClick={handleSend}
                    disabled={sending}
                    className="shrink-0 rounded bg-primary px-3 py-1 text-xs text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                  >
                    {sending ? "Sending…" : "Send ▶"}
                  </button>
                </div>
              </div>

              {/* Response */}
              <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded border bg-card">
                <ResponseMeta
                  statusCode={response?.statusCode ?? null}
                  elapsedMs={response?.elapsedMs ?? null}
                  bodyLength={response?.body?.length ?? null}
                  streaming={streaming}
                />
                <div className="min-h-0 flex-1 overflow-auto">
                  <BodyViewer body={response?.body ?? null} contentType="" />
                </div>
                {hasScriptOutput && (
                  <div className="shrink-0 border-t">
                    <ScriptOutputView
                      scriptLogs={response?.scriptLogs ?? []}
                      scriptError={response?.scriptError ?? null}
                      scriptSuggestion={response?.scriptSuggestion ?? null}
                      streaming={streaming}
                    />
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center">
              <p className="text-sm text-muted-foreground">
                Use the navigation on the left to progress through the tutorial.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
