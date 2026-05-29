import { useEffect, useRef, useState } from "react";
import {
  stepToRequestDetail,
  useTutorialSend,
  useTutorialSteps,
} from "../api/tutorial";
import { RequestResponseWorkbench } from "../components/layout/RequestResponseWorkbench";
import { useRequestStore } from "../store/requestStore";
import { useResponseStore } from "../store/responseStore";
import { useSessionStore } from "../store/sessionStore";

export function TutorialView() {
  const { data: steps = [] } = useTutorialSteps();
  const { send, cancel } = useTutorialSend();
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());

  // Snapshot the shared stores on mount; restore on unmount so the tutorial
  // never disturbs the workspace's in-progress request/response/session.
  const snapshotRef = useRef<{
    request: ReturnType<typeof useRequestStore.getState>;
    response: ReturnType<typeof useResponseStore.getState>;
    session: ReturnType<typeof useSessionStore.getState>;
  } | null>(null);
  useEffect(() => {
    snapshotRef.current = {
      request: { ...useRequestStore.getState() },
      response: { ...useResponseStore.getState() },
      session: { ...useSessionStore.getState() },
    };
    return () => {
      const snap = snapshotRef.current;
      if (!snap) return;
      useRequestStore.setState(snap.request);
      useResponseStore.setState(snap.response);
      useSessionStore.setState(snap.session);
    };
  }, []);

  const step = steps[currentStep];

  // Seed the shared stores from the current step.
  useEffect(() => {
    if (!step) return;
    if (step.method) {
      useRequestStore.getState().load(stepToRequestDetail(step));
    }
    useResponseStore.getState().reset();
    useSessionStore.getState().setVariables(step.variable_overrides ?? {});
  }, [step]);

  if (!step) return null;

  const goToStep = (i: number) => setCurrentStep(i);
  const handleNext = () => {
    setCompletedSteps((prev) => new Set(prev).add(currentStep));
    setCurrentStep((prev) => Math.min(prev + 1, steps.length - 1));
  };
  const handleBack = () => setCurrentStep((prev) => Math.max(prev - 1, 0));

  return (
    <div className="flex h-full overflow-hidden">
      {/* Coach rail */}
      <div className="flex w-72 shrink-0 flex-col border-r bg-card p-4">
        <div className="mb-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Progress
          </div>
          <div className="flex flex-col gap-1">
            {steps.map((s, i) => (
              <button
                key={s.title}
                type="button"
                onClick={() => goToStep(i)}
                className={`flex items-center gap-2 rounded px-2 py-1.5 text-left text-xs ${
                  i === currentStep
                    ? "border border-primary bg-primary/10 text-primary"
                    : completedSteps.has(i)
                      ? "bg-green-500/10 text-green-700 dark:text-green-400"
                      : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <span className="w-4 shrink-0 text-center">
                  {completedSteps.has(i) ? "✓" : i === currentStep ? "▶" : "○"}
                </span>
                {s.title}
              </button>
            ))}
          </div>
        </div>

        <div className="mb-4 min-h-0 flex-1 overflow-y-auto">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Instructions
          </div>
          <div className="whitespace-pre-wrap text-xs leading-relaxed text-foreground">
            {step.instructions}
          </div>
        </div>

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
            disabled={currentStep === steps.length - 1}
            className="flex-1 rounded bg-primary px-3 py-1.5 text-xs text-primary-foreground hover:bg-primary/90 disabled:opacity-30"
          >
            Next →
          </button>
        </div>
      </div>

      {/* Real request/response panes */}
      <div className="min-h-0 flex-1">
        {step.method ? (
          <RequestResponseWorkbench
            onSend={() => void send(currentStep)}
            onCancel={cancel}
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted-foreground">
              This step has no request — read the instructions and click Next.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
