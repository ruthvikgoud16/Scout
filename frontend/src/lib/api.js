import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

export const getStats = () => api.get("/stats").then((r) => r.data);
export const getCompanies = () => api.get("/companies").then((r) => r.data);
export const listHackathons = (params) =>
  api.get("/hackathons", { params }).then((r) => r.data);
export const getHackathon = (id) =>
  api.get(`/hackathons/${id}`).then((r) => r.data);
export const generatePrep = (id) =>
  api.post(`/hackathons/${id}/prep`).then((r) => r.data);
export const refreshFeed = () =>
  api.post("/hackathons/refresh").then((r) => r.data);
export const getResources = () => api.get("/resources").then((r) => r.data);

/** Server-Sent Events streaming chat using fetch. */
export async function* streamChat({ sessionId, message, hackathonId }) {
  const res = await fetch(`${API}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      hackathon_id: hackathonId,
    }),
  });
  if (!res.body) return;
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      try {
        const payload = JSON.parse(line.slice(5).trim());
        yield payload;
      } catch {
        // ignore
      }
    }
  }
}
