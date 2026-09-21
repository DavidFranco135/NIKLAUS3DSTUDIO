"use client";

import { useEffect, useRef } from "react";

const MODEL_VIEWER_SRC = "https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js";

function ensureModelViewerScript() {
  if (typeof document === "undefined") return;
  if (document.querySelector("script[data-model-viewer]")) return;
  const script = document.createElement("script");
  script.type = "module";
  script.src = MODEL_VIEWER_SRC;
  script.dataset.modelViewer = "true";
  document.head.appendChild(script);
}

export function ModelViewer({ src }: { src: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ensureModelViewerScript();
    const container = containerRef.current;
    if (!container) return;

    container.innerHTML = "";
    const element = document.createElement("model-viewer");
    element.setAttribute("src", src);
    element.setAttribute("camera-controls", "");
    element.setAttribute("auto-rotate", "");
    element.style.width = "100%";
    element.style.height = "100%";
    container.appendChild(element);
  }, [src]);

  return (
    <div
      ref={containerRef}
      className="h-80 w-full rounded border border-neutral-800 bg-neutral-900"
    />
  );
}
