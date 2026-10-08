import { useEffect, useRef, useState } from "react";
import { t } from "../locale/en";

// Bottom-fixed composer with auto-growing height, send button, and visible
// end-session / export-PDF affordances near it (not buried in a menu).
export default function Composer({
  onSend,
  disabled,
  onEnd,
  onExport,
  canEnd,
  canExport,
  notSaved,
}) {
  const [text, setText] = useState("");
  const taRef = useRef(null);

  useEffect(() => {
    const el = taRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 208) + "px";
    }
  }, [text]);

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  return (
    <div className="border-t border-neutral-200 bg-cream px-4 py-3">
      <div className="mx-auto max-w-3xl">
        {notSaved && (
          <div className="mb-1.5 flex items-center gap-1.5 text-xs text-amber-600">
            <span className="inline-block h-2 w-2 rounded-full bg-amber-500" />
            {t.notSaved}
          </div>
        )}
        <div className="flex items-end gap-2 rounded-2xl border border-neutral-300 bg-white px-4 py-2.5 shadow-sm focus-within:border-accent">
          <textarea
            ref={taRef}
            rows={1}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder={t.inputPlaceholder}
            className="max-h-52 flex-1 resize-none bg-transparent text-[15px] leading-6 outline-none"
          />
          <button
            onClick={submit}
            disabled={disabled || !text.trim()}
            className="rounded-lg bg-accent px-3.5 py-1.5 text-sm font-medium text-white disabled:opacity-40"
          >
            {t.send}
          </button>
        </div>
        <div className="mt-2 flex items-center gap-4 text-xs text-neutral-500">
          <button
            onClick={onEnd}
            disabled={!canEnd}
            className="flex items-center gap-1 disabled:opacity-40 hover:text-ink"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
            {t.endSession}
          </button>
          <button
            onClick={onExport}
            disabled={!canExport}
            className="flex items-center gap-1 disabled:opacity-40 hover:text-ink"
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M12 3v12m0 0l-4-4m4 4l4-4M4 21h16" />
            </svg>
            {t.exportPdf}
          </button>
        </div>
      </div>
    </div>
  );
}
