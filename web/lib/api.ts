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
