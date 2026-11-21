import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import {
  Background, Controls, MarkerType, ReactFlow, ReactFlowProvider, useReactFlow,
  type Connection, type Edge, type NodeChangeset, type EdgeChangeset, type OnSelectionChangeParams,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useTranslation } from "react-i18next";
import { useFlowsheet } from "@/state/FlowsheetProvider";
import { canConnect } from "@/state/flowsheet";
import { Palette, DRAG_TYPE } from "./Palette";
import { SidePanel, type Selection } from "./SidePanel";
import { UnitNode, type UnitNodeType } from "./UnitNode";
import { unitStatus, useIssues } from "./useIssues";

const NODE_TYPES = { unit: UnitNode };

/** Step 3: palette | canvas | side panel (DESIGN_SYSTEM.md → Layout). State = OPD document. */
export function FlowsheetPage() {
  return (
    <ReactFlowProvider>
      <FlowsheetEditor />
    </ReactFlowProvider>
  );
}

function FlowsheetEditor() {
  const { t } = useTranslation();
  const { doc, dispatch } = useFlowsheet();
  const issues = useIssues(doc);
  const flow = useReactFlow();
  const wrapper = useRef<HTMLDivElement>(null);
  const [selection, setSelection] = useState<Selection>(null);

  // React Flow keeps its own node/edge arrays (drag positions, selection, sizes);
  // they are rebuilt from the OPD document whenever the document changes.
  const [nodes, setNodes] = useState<UnitNodeType[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  useEffect(() => {
    setNodes((prev) =>
      doc.units.map((u, i) => {
        const old = prev.find((n) => n.id === u.id);
        return {
          ...(old ?? {}),
          id: u.id,
          type: "unit",
          position: doc.layout?.[u.id] ?? old?.position ?? { x: 80 + 160 * i, y: 120 },
          data: { unitType: u.type, label: u.label, status: unitStatus(u.id, doc, issues) },
        } as UnitNodeType;
      }),
    );
    setEdges((prev) =>
      doc.streams.map((s) => {
        const old = prev.find((e) => e.id === s.id);
        return {
          ...(old ?? {}),
          id: s.id,
          source: s.from.unit,
          sourceHandle: s.from.port,
          target: s.to.unit,
          targetHandle: s.to.port,
          label: s.id,
          type: "smoothstep",
          markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
        };
      }),
    );
  }, [doc, issues]);

  const onNodesChange = useCallback((changes: NodeChangeset<UnitNodeType>) => setNodes((n) => changes.applyTo(n)), []);
  const onEdgesChange = useCallback((changes: EdgeChangeset<Edge>) => setEdges((e) => changes.applyTo(e)), []);

  const toEndpoints = (c: Connection | Edge) => ({
    from: { unit: c.source, port: c.sourceHandle ?? "" },
    to: { unit: c.target, port: c.targetHandle ?? "" },
  });

  const isValidConnection = useCallback(
    (c: Connection | Edge) => {
      const { from, to } = toEndpoints(c);
      return canConnect(doc, from, to);
    },
    [doc],
  );

  const addUnit = useCallback(
    (unitType: string, position?: { x: number; y: number }) => {
      let pos = position;
      if (!pos) {
        const rect = wrapper.current?.getBoundingClientRect();
        const center = rect ? flow.screenToFlowPosition({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 }) : { x: 200, y: 150 };
        const n = doc.units.length % 6;
        pos = { x: center.x - 56 + n * 24, y: center.y - 32 + n * 24 };
      }
      dispatch({ type: "add_unit", unitType, x: Math.round(pos.x), y: Math.round(pos.y) });
    },
    [dispatch, doc.units.length, flow],
  );

  const onDrop = (e: DragEvent) => {
    const unitType = e.dataTransfer.getData(DRAG_TYPE);
    if (!unitType) return;
    e.preventDefault();
    const p = flow.screenToFlowPosition({ x: e.clientX, y: e.clientY });
    addUnit(unitType, { x: p.x - 56, y: p.y - 32 });
  };

  const onSelectionChange = useCallback(({ nodes: n, edges: e }: OnSelectionChangeParams) => {
    setSelection(n[0] ? { kind: "unit", id: n[0].id } : e[0] ? { kind: "stream", id: e[0].id } : null);
  }, []);

  const empty = useMemo(() => doc.units.length === 0, [doc.units.length]);

  return (
    <div className="flex h-full min-h-0">
      <h1 className="sr-only">{t("pages.flowsheet.title")}</h1>
      <Palette onAdd={(type) => addUnit(type)} />
      <div
        ref={wrapper}
        aria-label={t("flowsheet.canvas_label")}
        className="relative min-w-0 flex-1"
        onDragOver={(e) => {
          if (e.dataTransfer.types.includes(DRAG_TYPE)) {
            e.preventDefault();
            e.dataTransfer.dropEffect = "move";
          }
        }}
        onDrop={onDrop}
      >
        <ReactFlow<UnitNodeType, Edge>
          nodes={nodes}
          edges={edges}
          nodeTypes={NODE_TYPES}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeDragStop={(_, node) => dispatch({ type: "move_unit", id: node.id, x: Math.round(node.position.x), y: Math.round(node.position.y) })}
          onConnect={(c) => dispatch({ type: "connect", ...toEndpoints(c) })}
          isValidConnection={isValidConnection}
          onNodesDelete={(deleted) => deleted.forEach((n) => dispatch({ type: "remove_unit", id: n.id }))}
          onEdgesDelete={(deleted) => deleted.forEach((e) => dispatch({ type: "remove_stream", id: e.id }))}
          onSelectionChange={onSelectionChange}
          deleteKeyCode={["Delete", "Backspace"]}
          fitView
          fitViewOptions={{ maxZoom: 1, padding: 0.3 }}
          minZoom={0.3}
          maxZoom={2}
          proOptions={{ hideAttribution: false }}
        >
          <Background gap={16} size={1} color="var(--opd-border)" />
          <Controls showInteractive={false} />
        </ReactFlow>
        {empty && (
          <p className="pointer-events-none absolute inset-x-0 top-1/3 mx-auto max-w-sm text-center text-sm text-muted">
            {t("flowsheet.empty_canvas")}
          </p>
        )}
      </div>
      <SidePanel selection={selection} issues={issues} onDeleted={() => setSelection(null)} />
    </div>
  );
}
