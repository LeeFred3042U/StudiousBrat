export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export class ApiError extends Error {
  constructor(kind) {
    super(kind);
    this.kind = kind; // "network" | "db" | "http"
  }
}

async function request(path, options = {}) {
  let resp;
  try {
    resp = await fetch(API_BASE + path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (e) {
    throw new ApiError("network");
  }
  if (!resp.ok) {
    throw new ApiError(resp.status === 503 ? "db" : "http");
  }
  try {
    return await resp.json();
  } catch (e) {
    throw new ApiError("http");
  }
}

export const api = {
  createProfile: (profile) =>
    request("/profiles", { method: "POST", body: JSON.stringify(profile) }),
  patchProfile: (id, patch) =>
    request(`/profiles/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  deleteProfile: (id) => request(`/profiles/${id}`, { method: "DELETE" }),
  listSessions: (studentId) => request(`/profiles/${studentId}/sessions`),
  chat: (body) => request("/chat", { method: "POST", body: JSON.stringify(body) }),
  endSession: (id) => request(`/sessions/${id}/end`, { method: "POST" }),
  getSession: (id) => request(`/sessions/${id}`),
  exportPdf: (id) => request(`/sessions/${id}/export`, { method: "POST" }),
};
