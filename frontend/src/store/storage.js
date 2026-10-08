// localStorage write-through cache. Keeps the in-progress conversation when
// Neon (or the backend) is briefly unreachable, and queues unsent messages
// for retry on the next user action.
const PREFIX = "analogy-tutor:";

function readJSON(key, fallback) {
  try {
    const v = localStorage.getItem(PREFIX + key);
    return v ? JSON.parse(v) : fallback;
  } catch (e) {
    return fallback;
  }
}

function writeJSON(key, value) {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch (e) {
    /* storage full or unavailable — cache is best-effort */
  }
}

export const store = {
  getProfile: () => readJSON("profile", null),
  setProfile: (p) => writeJSON("profile", p),

  getLastSessionId: () => readJSON("lastSessionId", null),
  setLastSessionId: (id) => writeJSON("lastSessionId", id),

  getMessages: (sessionId) => readJSON("messages:" + sessionId, []),
  setMessages: (sessionId, msgs) => writeJSON("messages:" + sessionId, msgs),

  getUnsent: () => readJSON("unsent", []),
  queueUnsent: (payload) =>
    writeJSON("unsent", [...readJSON("unsent", []), payload]),
  clearUnsent: () => writeJSON("unsent", []),

  clearAll: () => {
    try {
      Object.keys(localStorage)
        .filter((k) => k.startsWith(PREFIX))
        .forEach((k) => localStorage.removeItem(k));
    } catch (e) {
      /* ignore */
    }
  },
};
