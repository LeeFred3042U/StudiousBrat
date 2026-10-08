import { t } from "../locale/en";

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  } catch (e) {
    return "";
  }
}

// Left sidebar: past sessions by topic + date, "New topic" at the top,
// profile/settings affordance at the bottom. Collapses to a drawer on mobile.
export default function Sidebar({
  open,
  onClose,
  sessions,
  activeId,
  profile,
  onNewTopic,
  onSelect,
  onOpenSettings,
  onOpenPrivacy,
}) {
  return (
    <>
      {open && (
        <div className="fixed inset-0 z-30 bg-black/30 md:hidden" onClick={onClose} />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-neutral-200 bg-cream transition-transform md:static md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="border-b border-neutral-200 p-4">
          <h1 className="font-serif text-lg font-bold">{t.appName}</h1>
          <button
            onClick={onNewTopic}
            className="mt-3 w-full rounded-lg bg-accent py-2 text-sm font-medium text-white shadow-sm hover:brightness-95"
          >
            {t.newTopic}
          </button>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          <div className="px-2 pb-1 text-[11px] uppercase tracking-wide text-neutral-400">
            {t.sessions}
          </div>
          {sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => onSelect(s.id)}
              className={`w-full rounded-lg px-2 py-2 text-left text-sm ${
                s.id === activeId ? "bg-white shadow-sm" : "hover:bg-white/60"
              }`}
            >
              <div className="truncate">{s.topic || t.untitledSession}</div>
              <div className="text-[11px] text-neutral-400">
                {formatDate(s.created_at)} · {s.status === "active" ? t.active : t.ended}
              </div>
            </button>
          ))}
        </nav>
        <div className="space-y-1 border-t border-neutral-200 p-3 text-sm">
          <button
            onClick={onOpenSettings}
            className="w-full rounded-lg px-2 py-1.5 text-left hover:bg-white/70"
          >
            {profile?.name || t.settings}
          </button>
          <button
            onClick={onOpenPrivacy}
            className="w-full rounded-lg px-2 py-1.5 text-left text-xs text-neutral-500 hover:bg-white/70"
          >
            {t.whatWeStore}
          </button>
        </div>
      </aside>
    </>
  );
}
