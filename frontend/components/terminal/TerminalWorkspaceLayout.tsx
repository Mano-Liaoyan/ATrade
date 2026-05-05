"use client";

import type { CSSProperties, PointerEvent, ReactNode } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  DEFAULT_TERMINAL_LAYOUT_PREFERENCES,
  createTerminalLayoutPreferences,
  readTerminalLayoutPreferences,
  resetTerminalLayoutPreferences,
  writeTerminalLayoutPreferences,
} from "@/lib/terminalLayoutPersistence";
import type { EnabledTerminalModuleId, TerminalLayoutPreferences } from "@/types/terminal";

type ResizeAxis = "context" | "monitor";

type TerminalWorkspaceLayoutProps = {
  activeModuleId: EnabledTerminalModuleId;
  children: ReactNode;
  context: ReactNode;
  monitor: ReactNode;
};

export function TerminalWorkspaceLayout({ activeModuleId, children, context, monitor }: TerminalWorkspaceLayoutProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [dragAxis, setDragAxis] = useState<ResizeAxis | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [preferences, setPreferences] = useState<TerminalLayoutPreferences>(DEFAULT_TERMINAL_LAYOUT_PREFERENCES);

  useEffect(() => {
    setPreferences(readTerminalLayoutPreferences());
    setHydrated(true);
  }, []);

  useEffect(() => {
    setPreferences((current) => createTerminalLayoutPreferences({ ...current, activeModuleId }));
  }, [activeModuleId]);

  useEffect(() => {
    if (hydrated) {
      writeTerminalLayoutPreferences(preferences);
    }
  }, [hydrated, preferences]);

  const updateSizeFromPointer = useCallback((clientX: number, clientY: number) => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const rect = container.getBoundingClientRect();
    if (dragAxis === "context") {
      const context = ((rect.right - clientX) / rect.width) * 100;
      setPreferences((current) => createTerminalLayoutPreferences({ ...current, sizes: { ...current.sizes, context } }));
    }

    if (dragAxis === "monitor") {
      const monitor = ((rect.bottom - clientY) / rect.height) * 100;
      setPreferences((current) => createTerminalLayoutPreferences({ ...current, sizes: { ...current.sizes, monitor } }));
    }
  }, [dragAxis]);

  useEffect(() => {
    if (!dragAxis) {
      return;
    }

    function handlePointerMove(event: globalThis.PointerEvent) {
      event.preventDefault();
      updateSizeFromPointer(event.clientX, event.clientY);
    }

    function handlePointerUp() {
      setDragAxis(null);
    }

    window.addEventListener("pointermove", handlePointerMove, { passive: false });
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerUp);
    };
  }, [dragAxis, updateSizeFromPointer]);

  const layoutStyle = useMemo(
    () => ({
      "--terminal-primary-size": `${preferences.sizes.primary}%`,
      "--terminal-context-size": `${preferences.sizes.context}%`,
      "--terminal-monitor-size": `${preferences.sizes.monitor}%`,
    }) as CSSProperties,
    [preferences.sizes.context, preferences.sizes.monitor, preferences.sizes.primary],
  );

  function startResize(axis: ResizeAxis, event: PointerEvent<HTMLButtonElement>) {
    event.preventDefault();
    setDragAxis(axis);
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  function resetLayout() {
    const resetPreferences = resetTerminalLayoutPreferences();
    setPreferences(createTerminalLayoutPreferences({ ...resetPreferences, activeModuleId }));
  }

  return (
    <section
      className={dragAxis ? "terminal-workspace-layout terminal-workspace-layout--resizing" : "terminal-workspace-layout"}
      data-testid="terminal-workspace-layout"
      ref={containerRef}
      style={layoutStyle}
    >
      <div className="terminal-workspace-layout__primary" data-layout-region="primary">
        {children}
      </div>

      <button
        aria-label="Resize primary and context panels"
        className="terminal-workspace-layout__splitter terminal-workspace-layout__splitter--vertical"
        data-testid="terminal-context-splitter"
        type="button"
        onPointerDown={(event) => startResize("context", event)}
      />

      <aside className="terminal-workspace-layout__context" data-layout-region="context" aria-label="Workspace context panel">
        {context}
      </aside>

      <button
        aria-label="Resize monitor panel"
        className="terminal-workspace-layout__splitter terminal-workspace-layout__splitter--horizontal"
        data-testid="terminal-monitor-splitter"
        type="button"
        onPointerDown={(event) => startResize("monitor", event)}
      />

      <section className="terminal-workspace-layout__monitor" data-layout-region="monitor" aria-label="Workspace monitor strip">
        {monitor}
      </section>

      <button className="terminal-workspace-layout__reset" data-testid="terminal-layout-reset" type="button" onClick={resetLayout}>
        Reset layout
      </button>
    </section>
  );
}
