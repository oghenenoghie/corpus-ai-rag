"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { createCollection, getLocalOwnerId, listCollections, type Collection } from "@/lib/api";

export default function CollectionsPage() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listCollections()
      .then(setCollections)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const collection = await createCollection(name.trim(), getLocalOwnerId());
      setCollections((prev) => [collection, ...prev]);
      setName("");
    } catch (e) {
      setError(String(e));
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="font-[family-name:var(--font-display)] text-3xl text-ink">Collections</h1>

      <form onSubmit={handleCreate} className="mt-8 flex gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New collection name"
          className="flex-1 rounded-md border border-rule bg-sheet px-3 py-2 text-ink outline-none focus:border-indigo"
        />
        <button
          type="submit"
          disabled={creating}
          className="rounded-md bg-indigo px-4 py-2 text-sheet disabled:opacity-50"
        >
          Create
        </button>
      </form>

      {error && <p className="mt-4 text-oxide">{error}</p>}

      <ul className="mt-8 divide-y divide-rule">
        {loading && <li className="py-3 text-sepia">Loading…</li>}
        {!loading && collections.length === 0 && (
          <li className="py-3 text-sepia">No collections yet — create one above.</li>
        )}
        {collections.map((c) => (
          <li key={c.id} className="py-3">
            <Link href={`/collections/${c.id}`} className="text-indigo hover:underline">
              {c.name}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
