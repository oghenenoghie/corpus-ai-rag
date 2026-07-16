"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useRef, useState } from "react";
import { listDocuments, uploadDocument, type DocumentStatus } from "@/lib/api";
import { UploadDropzone } from "@/components/upload-dropzone";
import { DocumentStatusBadge } from "@/components/document-status-badge";

const IN_PROGRESS: DocumentStatus["status"][] = ["pending", "parsing", "embedding"];
const POLL_INTERVAL_MS = 2000;

export default function CollectionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: collectionId } = use(params);
  const [documents, setDocuments] = useState<DocumentStatus[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      setDocuments(await listDocuments(collectionId));
    } catch (e) {
      setError(String(e));
    }
  }, [collectionId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Live ingestion progress: poll while anything is still pending/parsing/embedding.
  useEffect(() => {
    const anyInProgress = documents.some((d) => IN_PROGRESS.includes(d.status));
    if (anyInProgress && !pollRef.current) {
      pollRef.current = setInterval(refresh, POLL_INTERVAL_MS);
    }
    if (!anyInProgress && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [documents, refresh]);

  async function handleUpload(file: File) {
    setUploading(true);
    setError(null);
    try {
      await uploadDocument(collectionId, file);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <div className="flex items-baseline justify-between">
        <h1 className="font-[family-name:var(--font-display)] text-3xl text-ink">
          Collection documents
        </h1>
        <Link href={`/collections/${collectionId}/chat`} className="text-indigo hover:underline">
          Chat →
        </Link>
      </div>

      <div className="mt-8">
        <UploadDropzone onFileSelected={handleUpload} disabled={uploading} />
      </div>

      {error && <p className="mt-4 text-oxide">{error}</p>}

      <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {documents.length === 0 && (
          <p className="text-sepia">No documents yet — upload one above.</p>
        )}
        {documents.map((doc) => (
          <Link
            key={doc.id}
            href={`/collections/${collectionId}/doc/${doc.id}`}
            className="block rounded-lg border border-rule bg-sheet p-4 hover:border-indigo"
          >
            <div className="flex items-start justify-between gap-2">
              <p className="truncate text-ink">{doc.filename}</p>
              <DocumentStatusBadge status={doc.status} />
            </div>
            <p className="mt-1 font-[family-name:var(--font-mono)] text-xs text-sepia">
              {doc.page_count ? `${doc.page_count} pages` : "—"}
            </p>
            {doc.status === "failed" && doc.error && (
              <p className="mt-2 text-sm text-oxide">{doc.error}</p>
            )}
          </Link>
        ))}
      </div>
    </main>
  );
}
