import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";

interface TwoPanelProps {
  left: React.ReactNode;
  right: React.ReactNode;
  direction?: "horizontal" | "vertical";
  defaultSizes?: [number, number];
}

export function TwoPanel({
  left,
  right,
  direction = "horizontal",
  defaultSizes = [50, 50],
}: TwoPanelProps) {
  return (
    <PanelGroup direction={direction} className="h-full">
      <Panel defaultSize={defaultSizes[0]} minSize={10}>
        {left}
      </Panel>
      <PanelResizeHandle
        className={
          direction === "horizontal"
            ? "w-1 bg-gray-200 hover:bg-purple-400 cursor-col-resize"
            : "h-1 bg-gray-200 hover:bg-purple-400 cursor-row-resize"
        }
      />
      <Panel defaultSize={defaultSizes[1]} minSize={10}>
        {right}
      </Panel>
    </PanelGroup>
  );
}
