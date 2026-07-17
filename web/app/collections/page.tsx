"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { createCollection, getLocalOwnerId, listCollections, type Collection } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";

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
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New collection name"
        />
        <Button type="submit" disabled={creating}>
          Create
        </Button>
      </form>

      {error && <p className="mt-4 text-oxide">{error}</p>}

      <div className="mt-8 flex flex-col gap-3">
        {loading && <p className="text-sepia">Loading…</p>}
        {!loading && collections.length === 0 && (
          <p className="text-sepia">No collections yet — create one above.</p>
        )}
        {collections.map((c) => (
          <Link key={c.id} href={`/collections/${c.id}`}>
            <Card className="transition-colors hover:border-indigo">
              <CardHeader>
                <CardTitle>{c.name}</CardTitle>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </main>
  );
}
