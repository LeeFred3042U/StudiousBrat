import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { t } from "../locale/en";

mermaid.initialize({ startOnLoad: false, theme: "neutral" });

let renderCount = 0;

// Mermaid flowcharts render inline via the Mermaid.js client library.
export default function MermaidChart({ source }) {
  const boxRef = useRef(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const id = `analogy-tutor-mmd-${++renderCount}`;
    mermaid
      .render(id, source)
      .then(({ svg }) => {
        if (!cancelled && boxRef.current) boxRef.current.innerHTML = svg;
      })
      .catch(() => setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [source]);

  return (
    <div>
      <div className="mb-2 text-xs uppercase tracking-wide text-neutral-500">
        {t.flowchartTitle}
      </div>
      {failed ? (
        <pre className="overflow-x-auto rounded-lg border border-neutral-200 bg-white p-3 text-xs text-neutral-600">
          {source}
        </pre>
      ) : (
        <div ref={boxRef} className="mermaid-box overflow-x-auto rounded-lg border border-neutral-200 bg-white p-3" />
      )}
    </div>
  );
}
