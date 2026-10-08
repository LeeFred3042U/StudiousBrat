import { t } from "../locale/en";

// Subtle animated "thinking" dots while the orchestrator runs — matching a
// streaming feel rather than a blocking spinner.
export default function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2 text-neutral-400">
      <span className="flex gap-1">
        <span className="thinking-dot" />
        <span className="thinking-dot" />
        <span className="thinking-dot" />
      </span>
      <span className="text-sm">{t.thinking}</span>
    </div>
  );
}
