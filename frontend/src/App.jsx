import { useCallback, useEffect, useState } from "react";
import { api, API_BASE } from "./api/client";
import { store } from "./store/storage";
import { t } from "./locale/en";
import Sidebar from "./components/Sidebar";
import ChatPane from "./components/ChatPane";
import Onboarding from "./components/Onboarding";
import SettingsModal from "./components/SettingsModal";
import PrivacyModal from "./components/PrivacyModal";

export default function App() {
  const [profile, setProfile] = useState(() => store.getProfile());
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(() => store.getLastSessionId());
  const [messages, setMessages] = useState(() => {
    const sid = store.getLastSessionId();
    return sid ? store.getMessages(sid) : [];
  });
  const [thinking, setThinking] = useState(false);
  const [notSaved, setNotSaved] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showPrivacy, setShowPrivacy] = useState(false);

  const refreshSessions = useCallback(async () => {
    if (!profile) return null;
    try {
      const list = await api.listSessions(profile.id);
      setSessions(list);
      return list;
    } catch (e) {
      return null; // DB unreachable — keep working from cache
    }
  }, [profile]);

  const selectSession = async (sid) => {
    setActiveId(sid);
    store.setLastSessionId(sid);
    setSidebarOpen(false);
    try {
      const s = await api.getSession(sid);
      const msgs = s.messages.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        assets: [],
      }));
      // Restored assets attach to the last assistant message so flashcards,
      // flowcharts, memes and the teach-back card re-render inline.
      if (s.assets?.length && msgs.length) {
        for (let i = msgs.length - 1; i >= 0; i--) {
          if (msgs[i].role === "ai") {
            msgs[i].assets = s.assets;
            break;
          }
        }
      }
      setMessages(msgs);
      store.setMessages(sid, msgs);
      setNotSaved(false);
    } catch (e) {
      // Neon read failed: serve from the localStorage write-through cache.
      setMessages(store.getMessages(sid));
      setNotSaved(true);
    }
  };

  useEffect(() => {
    (async () => {
      if (!profile) return;
      const list = await refreshSessions();
      // Resume the most recent active session on load if none is open.
      if (!activeId && list && list.length > 0 && list[0].status === "active") {
        await selectSession(list[0].id);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile && profile.id]);

  const setAndCacheMessages = (sid, msgs) => {
    setMessages(msgs);
    if (sid) store.setMessages(sid, msgs);
  };

  const newTopic = () => {
    setActiveId(null);
    setMessages([]);
    setNotSaved(false);
    store.setLastSessionId(null);
    setSidebarOpen(false);
  };

  const send = async (text) => {
    if (!text.trim() || thinking) return;
    let sid = activeId;
    const studentMsg = {
      id: crypto.randomUUID(),
      role: "student",
      content: text,
      assets: [],
    };
    const withStudent = [...messages, studentMsg];
    setMessages(withStudent);
    if (sid) store.setMessages(sid, withStudent);
    setThinking(true);
    try {
      // Retry queued (unsaved) messages first — "retry on next user action".
      const unsent = store.getUnsent();
      if (unsent.length) {
        for (const u of unsent) {
          try {
            await api.chat(u);
          } catch (e) {
            /* keep going; still-queued items are retried next time */
          }
        }
        store.clearUnsent();
      }
      const res = await api.chat({
        student_id: profile.id,
        session_id: sid,
        message: text,
        new_session: !sid,
      });
      const aiMsg = {
        id: crypto.randomUUID(),
        role: "ai",
        content: res.reply,
        assets: res.assets || [],
      };
      if (!sid) {
        sid = res.session_id;
        setActiveId(sid);
        store.setLastSessionId(sid);
      }
      const updated = [...withStudent, aiMsg];
      setAndCacheMessages(sid, updated);
      setNotSaved(!res.persisted);
      refreshSessions();
    } catch (e) {
      // Network/DB failure: keep the conversation locally, queue the message,
      // and show only the plain generic message — never a raw error.
      store.queueUnsent({ student_id: profile.id, session_id: sid, message: text });
      setNotSaved(true);
      const errMsg = {
        id: crypto.randomUUID(),
        role: "ai",
        content: t.errorGeneric,
        assets: [],
      };
      const updated = [...withStudent, errMsg];
      if (sid) store.setMessages(sid, updated);
      setMessages(updated);
    } finally {
      setThinking(false);
    }
  };

  const endSession = async () => {
    if (!activeId || !window.confirm(t.endConfirm)) return;
    try {
      await api.endSession(activeId);
    } catch (e) {
      /* non-blocking */
    }
    setActiveId(null);
    setMessages([]);
    store.setLastSessionId(null);
    refreshSessions();
  };

  const exportPdf = async () => {
    if (!activeId) return;
    try {
      const { pdf_url } = await api.exportPdf(activeId);
      window.open(API_BASE + pdf_url, "_blank");
    } catch (e) {
      window.alert(t.errorGeneric);
    }
  };

  const deleteMyData = async () => {
    if (!profile || !window.confirm(t.deleteConfirm)) return;
    try {
      await api.deleteProfile(profile.id);
    } catch (e) {
      /* attempt anyway below so local state is consistent */
    }
    store.clearAll();
    setProfile(null);
    setSessions([]);
    setActiveId(null);
    setMessages([]);
    setShowSettings(false);
  };

  if (!profile) return <Onboarding onDone={setProfile} />;

  const activeTopic = sessions.find((s) => s.id === activeId)?.topic || "";

  return (
    <div className="flex h-screen overflow-hidden bg-cream text-ink">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        sessions={sessions}
        activeId={activeId}
        profile={profile}
        onNewTopic={newTopic}
        onSelect={selectSession}
        onOpenSettings={() => setShowSettings(true)}
        onOpenPrivacy={() => setShowPrivacy(true)}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-3 border-b border-neutral-200 px-4 py-3 md:hidden">
          <button onClick={() => setSidebarOpen(true)} aria-label={t.menu} className="p-1 text-lg">
            ☰
          </button>
          <span className="truncate font-serif font-bold">{activeTopic || t.appName}</span>
        </div>
        <ChatPane
          topic={activeTopic}
          messages={messages}
          thinking={thinking}
          notSaved={notSaved}
          onSend={send}
          onEnd={endSession}
          onExport={exportPdf}
          canEnd={!!activeId}
          canExport={!!activeId}
        />
      </div>
      {showSettings && (
        <SettingsModal
          profile={profile}
          onClose={() => setShowSettings(false)}
          onSave={setProfile}
          onDelete={deleteMyData}
        />
      )}
      {showPrivacy && <PrivacyModal onClose={() => setShowPrivacy(false)} />}
    </div>
  );
}
