import type { ReactNode } from "react";
import type { Citation } from "@/lib/api";

const CITATION_PATTERN = /\[(\d+)\]/g;

/** Renders message content, turning each "[n]" marker into a clickable
 * superscript wherever a citation's `span_start` lines up with it — the
 * exact offset the backend recorded when it parsed the marker out of the
 * stream (see api/app/generation.py). Markers with no matching span (a
 * hallucinated chunk number) render as plain text. */
export function CitationText({
  content,
  citations,
  onCitationClick,
}: {
  content: string;
  citations: Citation[];
  onCitationClick: (citation: Citation) => void;
}) {
  const citationBySpanStart = new Map(citations.map((c) => [c.span_start, c]));
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;

  for (const match of content.matchAll(CITATION_PATTERN)) {
    const index = match.index ?? 0;
    if (index > lastIndex) nodes.push(content.slice(lastIndex, index));

    const citation = citationBySpanStart.get(index);
    if (citation) {
      nodes.push(
        <sup
          key={key++}
          role="button"
          tabIndex={0}
          onClick={() => onCitationClick(citation)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") onCitationClick(citation);
          }}
          className="cursor-pointer px-0.5 font-[family-name:var(--font-mono)] text-oxide hover:underline"
        >
          {match[1]}
        </sup>,
      );
    } else {
      nodes.push(match[0]);
    }
    lastIndex = index + match[0].length;
  }
  if (lastIndex < content.length) nodes.push(content.slice(lastIndex));

  return <>{nodes}</>;
}
