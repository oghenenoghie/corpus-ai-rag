export default async function DocumentReaderPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string; docId: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const { docId } = await params;
  const { page } = await searchParams;

  return (
    <main className="h-screen">
      <iframe
        src={`/api/documents/${docId}/file${page ? `#page=${page}` : ""}`}
        className="h-full w-full"
        title="Document viewer"
      />
    </main>
  );
}
