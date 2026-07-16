import { cn } from "@/lib/utils";
import type { DocumentStatusValue } from "@/lib/api";

const STYLES: Record<DocumentStatusValue, string> = {
  pending: "bg-rule text-sepia",
  parsing: "bg-indigo/10 text-indigo",
  embedding: "bg-indigo/10 text-indigo",
  ready: "bg-moss/10 text-moss",
  failed: "bg-oxide/10 text-oxide",
};

const LABELS: Record<DocumentStatusValue, string> = {
  pending: "Pending",
  parsing: "Parsing",
  embedding: "Embedding",
  ready: "Ready",
  failed: "Failed",
};

export function DocumentStatusBadge({ status }: { status: DocumentStatusValue }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 font-[family-name:var(--font-mono)] text-xs",
        STYLES[status],
      )}
    >
      {LABELS[status]}
    </span>
  );
}
