import { useState } from "react";
import { useViewStore } from "../store/viewStore";

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
      "The simplest HTTP request is a GET with no parameters. It retrieves a resource and returns JSON.\n\nThis request fetches all museum departments — five major collection areas used to organize the Met's 1.5 million objects.\n\nClick Send to try it. The response appears on the right.",
    hasRequest: true,
    displayMethod: "GET",
    displayUrl: "http://localhost:8000/mock/met/departments",
  },
  {
    title: "Path parameters",
    instructions:
      "REST APIs use path parameters to identify a specific resource. Instead of listing all objects, you can fetch one by its ID.\n\nObject 45734 is Van Gogh's Self-Portrait with a Straw Hat (1887). The ID is embedded directly in the URL path.\n\nClick Send to retrieve it.",
    hasRequest: true,
    displayMethod: "GET",
    displayUrl: "http://localhost:8000/mock/met/objects/45734",
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
    displayUrl: "http://localhost:8000/mock/met/objects/45734",
  },
  {
    title: "Post-request scripts",
    instructions:
      'Post-request scripts run JavaScript after the HTTP call. They can read the response and extract data.\n\nThis script reads the JSON response and logs the artwork\'s details:\n\n  var obj = dm.response.json();\n  dm.console.log("Title:", obj.title);\n  dm.console.log("Artist:", obj.artistDisplayName);\n\nUse dm.env.set("key", value) to store response data as variables for use in later requests.\n\nClick Send to run it.',
    hasRequest: true,
    displayMethod: "GET",
    displayUrl: "http://localhost:8000/mock/met/objects/45734",
  },
];

interface LogEntry {
  id: string;
  text: string;
}

interface TutorialResponseState {
  statusCode: number | null;
  url: string | null;
  body: string | null;
  elapsedMs: number | null;
  scriptLogs: LogEntry[];
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

  const handleSend = async () => {
    setSending(true);
    setResponse(null);

    const res = await fetch(`/api/tutorial/steps/${currentStep}/send`, {
      method: "POST",
    });

    if (!res.ok || !res.body) {
      setResponse({
        statusCode: null,
        url: null,
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
      url: null,
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
              partial.url = data.url as string;
            } else if (event === "body") {
              partial.body = data.body as string;
              partial.elapsedMs = data.elapsed_ms as number;
            } else if (event === "done") {
              partial.scriptLogs = ((data.script_logs as string[]) ?? []).map(
                (text) => ({ id: crypto.randomUUID(), text }),
              );
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

  const hasScriptOutput =
    response !== null &&
    (response.scriptLogs.length > 0 || response.scriptError !== null);

  return (
    <div className="flex h-screen flex-col bg-gray-950 text-gray-100">
      {/* Nav bar */}
      <nav className="flex shrink-0 items-center gap-4 border-b border-gray-800 bg-gray-900 px-4 py-2">
        <span className="text-sm font-semibold text-gray-200">🥁 Drummer</span>
        <div className="flex gap-1">
          <button
            type="button"
            onClick={() => setView("workspace")}
            className="rounded px-3 py-1 text-xs text-gray-400 hover:text-gray-200"
          >
            Workspace
          </button>
          <button
            type="button"
            className="rounded bg-gray-700 px-3 py-1 text-xs text-white"
          >
            Tutorial
          </button>
        </div>
      </nav>

      {/* Two-column body */}
      <div className="flex min-h-0 flex-1 overflow-hidden">
        {/* Left column */}
        <div className="flex w-72 shrink-0 flex-col border-r border-gray-800 bg-gray-900 p-4">
          {/* Step list */}
          <div className="mb-4">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
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
                      ? "border border-blue-700 bg-blue-900/50 text-blue-300"
                      : completedSteps.has(i)
                        ? "bg-green-900/20 text-green-400"
                        : "text-gray-500 hover:text-gray-300"
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
            <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
              Instructions
            </div>
            <div className="whitespace-pre-wrap text-xs leading-relaxed text-gray-300">
              {step.instructions}
            </div>
          </div>

          {/* Back / Next */}
          <div className="flex gap-2 border-t border-gray-800 pt-3">
            <button
              type="button"
              onClick={handleBack}
              disabled={currentStep === 0}
              className="rounded bg-gray-800 px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 disabled:opacity-30"
            >
              ← Back
            </button>
            <button
              type="button"
              onClick={handleNext}
              disabled={currentStep === STEPS.length - 1}
              className="flex-1 rounded bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700 disabled:opacity-30"
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
                <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
                  Request
                </div>
                <div className="flex items-center gap-2 rounded bg-gray-800 px-3 py-2">
                  <span className="rounded bg-blue-800 px-2 py-0.5 text-xs font-semibold text-blue-200">
                    {step.displayMethod}
                  </span>
                  <span className="flex-1 truncate font-mono text-xs text-gray-200">
                    {step.displayUrl}
                  </span>
                  <button
                    type="button"
                    onClick={handleSend}
                    disabled={sending}
                    className="shrink-0 rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {sending ? "Sending…" : "Send ▶"}
                  </button>
                </div>
              </div>

              {/* Response */}
              {response && (
                <div className="flex min-h-0 flex-1 flex-col gap-2">
                  <div className="flex shrink-0 items-center gap-3">
                    <div className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                      Response
                    </div>
                    {response.statusCode !== null && (
                      <>
                        <span className="rounded bg-green-900 px-2 py-0.5 text-xs text-green-300">
                          {response.statusCode} OK
                        </span>
                        <span className="text-xs text-gray-500">
                          {response.elapsedMs?.toFixed(0)}ms
                        </span>
                      </>
                    )}
                    {response.error && (
                      <span className="text-xs text-red-400">
                        {response.error}
                      </span>
                    )}
                  </div>
                  {response.body && (
                    <pre className="min-h-0 flex-1 overflow-auto rounded border border-gray-800 bg-gray-950 p-3 font-mono text-xs text-blue-300">
                      {response.body}
                    </pre>
                  )}
                  {hasScriptOutput && (
                    <div className="shrink-0 rounded border border-gray-800 bg-gray-950 p-2 font-mono text-xs">
                      {response.scriptLogs.map(({ id, text }) => (
                        <div key={id} className="text-amber-300">
                          {text}
                        </div>
                      ))}
                      {response.scriptError && (
                        <div className="text-red-400">
                          {response.scriptError}
                        </div>
                      )}
                      {response.scriptSuggestion && (
                        <div className="italic text-amber-500">
                          Hint: {response.scriptSuggestion}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center">
              <p className="text-sm text-gray-500">
                Use the navigation on the left to progress through the tutorial.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
