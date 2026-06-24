import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import "@/App.css";
import { Toaster } from "@/components/ui/sonner";
import Layout from "@/components/Layout";
import Home from "@/pages/Home";
import Hackathons from "@/pages/Hackathons";
import HackathonDetail from "@/pages/HackathonDetail";
import Resources from "@/pages/Resources";
import Login, { Register } from "@/pages/Login";
import AuthCallback from "@/pages/AuthCallback";
import Dashboard from "@/pages/Dashboard";
import AIAssistant from "@/components/AIAssistant";
import { AuthProvider } from "@/lib/auth";

function AppRouter() {
  const loc = useLocation();
  // Handle Google OAuth callback fragment synchronously BEFORE any other route
  if (loc.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/hackathons" element={<Hackathons />} />
        <Route path="/hackathons/:id" element={<HackathonDetail />} />
        <Route path="/resources" element={<Resources />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </Layout>
  );
}

function App() {
  return (
    <div className="App min-h-screen bg-[var(--bg)] text-[var(--ink)]">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
          <AIAssistant />
          <Toaster position="bottom-right" richColors />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
