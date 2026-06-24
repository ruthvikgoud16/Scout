import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, API } from "@/lib/api";

const TOKEN_KEY = "ot_token";
const AuthCtx = createContext(null);

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    localStorage.removeItem(TOKEN_KEY);
    delete api.defaults.headers.common["Authorization"];
  }
}

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY);
}

// init existing token on module load
const _t = getAuthToken();
if (_t) api.defaults.headers.common["Authorization"] = `Bearer ${_t}`;

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const token = getAuthToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      setAuthToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Skip auth check if we're processing a Google OAuth callback (#session_id=...)
    if (window.location.hash?.includes("session_id=")) {
      setLoading(false);
      return;
    }
    refresh();
  }, [refresh]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    setAuthToken(data.token);
    setUser(data.user);
    return data.user;
  };

  const register = async (email, password, name) => {
    const { data } = await api.post("/auth/register", { email, password, name });
    setAuthToken(data.token);
    setUser(data.user);
    return data.user;
  };

  const googleExchange = async (sessionId) => {
    const { data } = await api.post("/auth/google-session", {
      session_id: sessionId,
    });
    setAuthToken(data.token);
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {}
    setAuthToken(null);
    setUser(null);
  };

  return (
    <AuthCtx.Provider
      value={{ user, loading, refresh, login, register, googleExchange, logout, setUser }}
    >
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  return useContext(AuthCtx);
}

// Helper used by Layout to start Google OAuth
export function startGoogleAuth(redirectPath = "/dashboard") {
  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  const redirectUrl = window.location.origin + redirectPath;
  window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(
    redirectUrl
  )}`;
}

// Direct endpoint helpers
export const me = {
  toggleBookmark: (hid) => api.post(`/me/bookmarks/${hid}`).then((r) => r.data),
  listBookmarks: () => api.get("/me/bookmarks").then((r) => r.data),
  setSkills: (skills) => api.put("/me/skills", { skills }).then((r) => r.data),
  feed: () => api.get("/me/feed").then((r) => r.data),
  uploadResume: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return api
      .post("/me/resume", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
  setNotify: (enabled) =>
    api.put(`/me/notify?enabled=${enabled}`).then((r) => r.data),
};

export const icsUrl = (hid) => `${API}/hackathons/${hid}/ics`;
