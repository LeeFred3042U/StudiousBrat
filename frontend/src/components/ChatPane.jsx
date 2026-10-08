import { useEffect, useRef } from "react";
import Message from "./Message";
import Composer from "./Composer";
import ThinkingIndicator from "./ThinkingIndicator";
import { t } from "../locale/en";

export default function ChatPane({
  topic,
  messages,
  thinking,
  notSaved,
  onSend,
  onEnd,
  onExport,
  canEnd,
  canExport,
}) {
  const bottomRef = useRef(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking]);

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <div className="hidden border-b border-neutral-200 px-6 py-3 md:block">
        <span className="font-serif text-lg font-bold">{topic || t.appName}</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-8 px-4 py-8">
          {messages.length === 0 && !thinking && (
            <div className="py-24 text-center text-neutral-400">
              <p className="font-serif text-2xl">{t.emptyStateTitle}</p>
              <p className="mx-auto mt-2 max-w-md text-sm">{t.emptyStateBody}</p>
            </div>
          )}
          {messages.map((m) => (
            <Message key={m.id} msg={m} />
          ))}
          {thinking && <ThinkingIndicator />}
          <div ref={bottomRef} />
        </div>
      </div>
      <Composer
        onSend={onSend}
        disabled={thinking}
        onEnd={onEnd}
        onExport={onExport}
        canEnd={canEnd}
        canExport={canExport}
        notSaved={notSaved}
      />
    </div>
  );
}
