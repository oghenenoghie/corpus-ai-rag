"use client";

import { use, useEffect, useRef, useState } from "react";
import {
  createConversation,
  streamQuery,
  type Citation,
  type Message,
} from "@/lib/api";
import { CitationText } from "@/components/citation-text";

export default function ChatPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: collectionId } = use(params);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [pendingAnswer, setPendingAnswer] = useState("");
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeDoc, setActiveDoc] = useState<{ documentId: string; page: number | null } | null>(
    null,
  );
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    createConversation(collectionId)
      .then((c) => setConversationId(c.id))
      .catch((e) => setError(String(e)));
  }, [collectionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pendingAnswer]);

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault();
    if (!conversationId || !question.trim() || busy) return;

    const asked = question.trim();
    setQuestion("");
    setBusy(true);
    setError(null);
    setPendingAnswer("");
    setMessages((prev) => [
      ...prev,
      {
        id: `local-q-${Date.now()}`,
        role: "user",
        content: asked,
        created_at: new Date().toISOString(),
        citations: [],
      },
    ]);

    let accumulated = "";
    let finalCitations: Citation[] = [];

    try {
      await streamQuery(conversationId, asked, (evt) => {
        if (evt.event === "token") {
          accumulated += evt.data.text;
          setPendingAnswer(accumulated);
        } else if (evt.event === "citations") {
          finalCitations = evt.data.citations;
        } else if (evt.event === "error") {
          setError(evt.data.detail);
        }
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setMessages((prev) => [
        ...prev,
        {
          id: `local-a-${Date.now()}`,
          role: "assistant",
          content: accumulated,
          created_at: new Date().toISOString(),
          citations: finalCitations,
        },
      ]);
      setPendingAnswer("");
      setBusy(false);
    }
  }

  function handleCitationClick(citation: Citation) {
    setActiveDoc({ documentId: citation.document_id, page: citation.page_number });
  }

  return (
    <main className="flex h-screen">
      <section className="flex w-1/2 flex-col border-r border-rule">
        <div className="flex-1 overflow-y-auto px-6 py-8">
          {messages.length === 0 && !busy && (
            <p className="text-sepia">Ask a question about this collection.</p>
          )}
          {messages.map((m) => (
            <div key={m.id} className={m.role === "user" ? "mb-4 text-right" : "mb-4"}>
              {m.role === "user" ? (
                <p className="inline-block rounded-lg bg-indigo/10 px-3 py-2 text-ink">
                  {m.content}
                </p>
              ) : (
                <p className="font-[family-name:var(--font-display)] leading-[1.7] text-ink">
                  <CitationText
                    content={m.content}
                    citations={m.citations}
                    onCitationClick={handleCitationClick}
                  />
                </p>
              )}
            </div>
          ))}
          {busy && (
            <p className="font-[family-name:var(--font-display)] leading-[1.7] text-ink">
              {pendingAnswer}
              <span className="animate-pulse">▍</span>
            </p>
          )}
          {error && <p className="mt-2 text-oxide">{error}</p>}
          <div ref={bottomRef} />
        </div>
        <form onSubmit={handleAsk} className="flex gap-2 border-t border-rule p-4">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about this collection…"
            disabled={busy || !conversationId}
            className="flex-1 rounded-md border border-rule bg-sheet px-3 py-2 text-ink outline-none focus:border-indigo"
          />
          <button
            type="submit"
            disabled={busy || !conversationId}
            className="rounded-md bg-indigo px-4 py-2 text-sheet disabled:opacity-50"
          >
            Ask
          </button>
        </form>
      </section>

      <section className="w-1/2 bg-parchment">
        {activeDoc ? (
          <iframe
            key={`${activeDoc.documentId}-${activeDoc.page ?? 0}`}
            src={`/api/documents/${activeDoc.documentId}/file${
              activeDoc.page ? `#page=${activeDoc.page}` : ""
            }`}
            className="h-full w-full"
            title="Document viewer"
          />
        ) : (
          <div className="flex h-full items-center justify-center px-8 text-center text-sepia">
            Click a citation marker to open its source document here.
          </div>
        )}
      </section>
    </main>
  );
}
