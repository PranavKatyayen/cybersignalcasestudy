"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { SparkleIcon } from "@/components/icons";

interface ChatAccount {
  entity_key: string;
  tier: string;
  score: number;
}
interface Msg {
  role: "user" | "assistant";
  text: string;
  accounts?: ChatAccount[];
  filters?: Record<string, unknown> | null;
  error?: boolean;
}

const SUGGESTIONS = [
  "Which critical accounts should I call first?",
  "Show high-confidence critical accounts in Japan",
  "How is the score calculated?",
];

function describeFilters(f: Record<string, unknown> | null | undefined): string | null {
  if (!f) return null;
  const parts: string[] = [];
  if (Array.isArray(f.tiers) && f.tiers.length) parts.push(`tier ${f.tiers.join("/")}`);
  if (f.country) parts.push(`country ${f.country}`);
  if (typeof f.minScore === "number") parts.push(`score >= ${f.minScore}`);
  if (f.confidence) parts.push(`${f.confidence} confidence`);
  if (f.text) parts.push(`matching "${f.text}"`);
  return parts.length ? `Filters applied: ${parts.join(", ")}` : "No filters: top-ranked accounts";
}

export function ChatWidget() {
  const pathname = usePathname();
  const accountKey = pathname.startsWith("/accounts/") ? decodeURIComponent(pathname.split("/")[2] ?? "") : null;

  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function send(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: q, accountKey }),
      });
      const data = await res.json();
      if (!res.ok) {
        setMessages((m) => [...m, { role: "assistant", text: data.error ?? "Something went wrong.", error: true }]);
      } else {
        setMessages((m) => [...m, { role: "assistant", text: data.answer, accounts: data.accounts, filters: data.filters }]);
      }
    } catch {
      setMessages((m) => [...m, { role: "assistant", text: "Network error. Please try again.", error: true }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-5 right-5 z-20 flex items-center gap-2 rounded-full bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-lg transition hover:bg-indigo-700"
        >
          <SparkleIcon className="h-4 w-4" />
          Ask CyberSignal
        </button>
      )}

      {open && (
        <div className="fixed bottom-5 right-5 z-20 flex h-[540px] w-[380px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
          <div className="flex items-center justify-between border-b border-slate-200 bg-indigo-600 px-4 py-3 text-white">
            <div>
              <div className="flex items-center gap-1.5 text-sm font-semibold">
                <SparkleIcon className="h-4 w-4" /> Ask CyberSignal
              </div>
              <div className="text-[11px] text-indigo-100">
                {accountKey ? `Context: ${accountKey}` : "Answers only from your ranked account data"}
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="rounded px-2 text-lg leading-none hover:bg-indigo-500" aria-label="Close">
              &times;
            </button>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3 text-sm">
            {messages.length === 0 && (
              <div className="space-y-2">
                <p className="text-slate-500">Ask about which accounts to prioritise, why one ranks where it does, or how scoring works.</p>
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="block w-full rounded-lg border border-slate-200 px-3 py-2 text-left text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div
                  className={`max-w-[88%] rounded-2xl px-3.5 py-2.5 leading-relaxed ${
                    m.role === "user"
                      ? "bg-indigo-600 text-white"
                      : m.error
                      ? "bg-red-50 text-red-700"
                      : "bg-slate-100 text-slate-800"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.text}</p>
                  {m.accounts && m.accounts.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {m.accounts.map((a) => (
                        <Link
                          key={a.entity_key}
                          href={`/accounts/${encodeURIComponent(a.entity_key)}`}
                          className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-[11px] font-medium text-indigo-700 hover:bg-indigo-50"
                        >
                          {a.entity_key} &middot; {a.tier}
                        </Link>
                      ))}
                    </div>
                  )}
                  {describeFilters(m.filters) && <p className="mt-2 text-[11px] text-slate-400">{describeFilters(m.filters)}</p>}
                </div>
              </div>
            ))}
            {busy && <div className="text-xs text-slate-400">Thinking&hellip;</div>}
            <div ref={endRef} />
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex gap-2 border-t border-slate-200 p-3"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              maxLength={500}
              placeholder="Ask a question..."
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-400"
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              className="rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-semibold text-white disabled:opacity-40"
            >
              Send
            </button>
          </form>
          <div className="border-t border-slate-100 px-4 py-1.5 text-center text-[10px] text-slate-400">
            AI answers come from the account data only and can be wrong. Scores are rule-based.
          </div>
        </div>
      )}
    </>
  );
}
