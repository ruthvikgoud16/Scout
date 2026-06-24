import { useEffect, useRef, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { MessageSquare, Send, X, Sparkles, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { streamChat } from "@/lib/api";

const SESSION_KEY = "hacktrack_session_id";

function getSession() {
  let s = localStorage.getItem(SESSION_KEY);
  if (!s) {
    s = `s_${Math.random().toString(36).slice(2)}_${Date.now()}`;
    localStorage.setItem(SESSION_KEY, s);
  }
  return s;
}

export default function AIAssistant() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hey! I'm HackPilot 🚀 — ask me anything about prepping for hiring hackathons, building projects, system design, or how to crack a specific company's interview.",
    },
  ]);
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);
  const loc = useLocation();
  const params = useParams();
  const hackathonId =
    loc.pathname.startsWith("/hackathons/") && params.id ? params.id : null;

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, open]);

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setMessages((m) => [
      ...m,
      { role: "user", content: text },
      { role: "assistant", content: "" },
    ]);
    setBusy(true);
    try {
      for await (const payload of streamChat({
        sessionId: getSession(),
        message: text,
        hackathonId,
      })) {
        if (payload.delta) {
          setMessages((m) => {
            const copy = [...m];
            copy[copy.length - 1] = {
              role: "assistant",
              content: copy[copy.length - 1].content + payload.delta,
            };
            return copy;
          });
        }
        if (payload.error) {
          setMessages((m) => {
            const copy = [...m];
            copy[copy.length - 1] = {
              role: "assistant",
              content:
                "Sorry, I hit an error. Please try again in a moment. 🙏",
            };
            return copy;
          });
          break;
        }
        if (payload.done) break;
      }
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: "Connection lost. Please retry.",
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          data-testid="open-assistant"
          className="fixed bottom-6 right-6 z-40 group inline-flex items-center gap-2 bg-zinc-950 text-white px-4 py-3 hover:bg-[var(--brand)] transition-colors shadow-xl"
        >
          <Sparkles className="w-4 h-4" />
          <span className="text-sm font-semibold">Ask HackPilot</span>
        </button>
      )}

      {open && (
        <div
          className="fixed bottom-6 right-6 z-40 w-[92vw] sm:w-[420px] h-[70vh] sm:h-[560px] bg-white border border-zinc-300 shadow-2xl flex flex-col"
          data-testid="assistant-panel"
        >
          <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 bg-zinc-950 text-white">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[var(--live)]" />
              <div>
                <div className="text-sm font-semibold">HackPilot AI</div>
                <div className="text-[10px] uppercase tracking-wider text-zinc-400">
                  Powered by Gemini 3
                </div>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              data-testid="close-assistant"
              className="text-zinc-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <ScrollArea className="flex-1 px-4 py-4 bg-blue-50/40" ref={scrollRef}>
            <div className="space-y-4">
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={`flex ${
                    m.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[85%] px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
                      m.role === "user"
                        ? "bg-zinc-950 text-white"
                        : "bg-white border border-zinc-200"
                    }`}
                    data-testid={`msg-${m.role}-${i}`}
                  >
                    {m.content || (busy && i === messages.length - 1 ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      ""
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>

          <div className="border-t border-zinc-200 p-3 flex items-center gap-2 bg-white">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder="Ask about prep, rounds, projects…"
              className="rounded-none border-zinc-300 h-11 font-mono text-sm"
              disabled={busy}
              data-testid="assistant-input"
            />
            <Button
              onClick={send}
              disabled={busy || !input.trim()}
              className="rounded-none bg-zinc-950 hover:bg-[var(--brand)] h-11 px-4"
              data-testid="assistant-send"
            >
              {busy ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
