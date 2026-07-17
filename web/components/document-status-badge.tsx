import { Badge, type BadgeProps } from "@/components/ui/badge";
import type { DocumentStatusValue } from "@/lib/api";

const VARIANT: Record<DocumentStatusValue, NonNullable<BadgeProps["variant"]>> = {
  pending: "default",
  parsing: "info",
  embedding: "info",
  ready: "success",
  failed: "destructive",
};

const LABELS: Record<DocumentStatusValue, string> = {
  pending: "Pending",
  parsing: "Parsing",
  embedding: "Embedding",
  ready: "Ready",
  failed: "Failed",
};

export function DocumentStatusBadge({ status }: { status: DocumentStatusValue }) {
  return <Badge variant={VARIANT[status]}>{LABELS[status]}</Badge>;
}
