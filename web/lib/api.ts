// All requests go through the relative `/api` prefix, which next.config.ts
// rewrites to the FastAPI backend. Keeping requests same-origin from the
// browser's perspective means the backend never needs CORS configured.
const BASE = "/api";

export type DocumentStatusValue = "pending" | "parsing" | "embedding" | "ready" | "failed";

export type DocumentStatus = {
  id: string;
  filename: string;
  page_count: number | null;
  status: DocumentStatusValue;
  error: string | null;
};

export type Collection = {
  id: string;
  name: string;
  owner_id: string;
};

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { ...init, cache: "no-store" });
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status} ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export function listCollections(): Promise<Collection[]> {
  return apiFetch<Collection[]>("/collections");
}

export function createCollection(name: string, ownerId: string): Promise<Collection> {
  return apiFetch<Collection>("/collections", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, owner_id: ownerId }),
  });
}

export function listDocuments(collectionId: string): Promise<DocumentStatus[]> {
  return apiFetch<DocumentStatus[]>(`/collections/${collectionId}/documents`);
}

export function getDocumentStatus(documentId: string): Promise<DocumentStatus> {
  return apiFetch<DocumentStatus>(`/documents/${documentId}/status`);
}

export async function uploadDocument(
  collectionId: string,
  file: File,
): Promise<{ document_id: string; status: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/ingest?collection_id=${encodeURIComponent(collectionId)}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    throw new Error(`upload failed: ${res.status} ${await res.text()}`);
  }
  return res.json();
}

export type Citation = {
  id: string;
  chunk_id: string;
  span_start: number;
  span_end: number;
  document_id: string;
  page_number: number | null;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  citations: Citation[];
};

export type Conversation = {
  id: string;
  collection_id: string;
  title: string | null;
};

export type RetrievedChunkInfo = {
  id: string;
  document_id: string;
  page_number: number | null;
  heading_path: string[];
  score: number;
};

export type QueryEvent =
  | { event: "retrieval"; data: { chunks: RetrievedChunkInfo[] } }
  | { event: "token"; data: { text: string } }
  | { event: "citations"; data: { citations: Citation[] } }
  | { event: "done"; data: { message_id: string } }
  | { event: "error"; data: { detail: string } };

export function createConversation(collectionId: string, title?: string): Promise<Conversation> {
  return apiFetch<Conversation>(`/collections/${collectionId}/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: title ?? null }),
  });
}

export function listConversations(collectionId: string): Promise<Conversation[]> {
  return apiFetch<Conversation[]>(`/collections/${collectionId}/conversations`);
}

export function listMessages(conversationId: string): Promise<Message[]> {
  return apiFetch<Message[]>(`/conversations/${conversationId}/messages`);
}

/** POST /query streams SSE ("event: x\ndata: y\n\n" frames), which the
 * browser's EventSource can't do (it's GET-only) — so this parses the
 * stream by hand off a plain fetch response body reader. */
export async function streamQuery(
  conversationId: string,
  question: string,
  onEvent: (event: QueryEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, question }),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`query failed: ${res.status} ${await res.text()}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let frameEnd: number;
    while ((frameEnd = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, frameEnd);
      buffer = buffer.slice(frameEnd + 2);

      let eventName = "message";
      let dataLine = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event: ")) eventName = line.slice(7);
        else if (line.startsWith("data: ")) dataLine = line.slice(6);
      }
      if (dataLine) {
        onEvent({ event: eventName, data: JSON.parse(dataLine) } as QueryEvent);
      }
    }
  }
}

const OWNER_ID_KEY = "corpus:owner-id";

/** No auth yet (out of scope for Phase 1) — persist a per-browser owner id
 * so repeat visits see the same collections. */
export function getLocalOwnerId(): string {
  let id = localStorage.getItem(OWNER_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(OWNER_ID_KEY, id);
  }
  return id;
}
