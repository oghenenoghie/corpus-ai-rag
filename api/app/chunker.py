from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import tiktoken

from app.config import RetrievalConfig
from app.pdf_parser import ParsedBlock


@lru_cache(maxsize=1)
def _get_encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


# A line is treated as a heading if it's meaningfully larger than body text,
# or bold and at least as large as body text. PDFs carry no semantic
# heading tags, so font metrics are the only structural signal available.
_HEADING_SIZE_RATIO = 1.15


@dataclass
class ChunkDraft:
    """Everything needed for one row in `chunks`. `content` is the raw
    text (what's shown to the user / cited); `embedding_text` is what
    actually gets embedded — heading path prepended, since a chunk like
    "It shall not exceed 30 days" is meaningless without knowing it's under
    "Chapter 3 > Warranty Terms"."""

    content: str
    embedding_text: str
    page_number: int
    bbox: dict[str, Any]
    token_count: int
    chunk_index: int
    heading_path: list[str] = field(default_factory=list)


def _detect_body_font_size(blocks: list[ParsedBlock]) -> float:
    if not blocks:
        return 10.0
    counts = Counter(round(b.font_size, 1) for b in blocks)
    return counts.most_common(1)[0][0]


def _is_heading(block: ParsedBlock, body_size: float) -> bool:
    if block.font_size >= body_size * _HEADING_SIZE_RATIO:
        return True
    return block.is_bold and block.font_size > body_size


def _assign_heading_paths(blocks: list[ParsedBlock], body_size: float) -> list[list[str]]:
    """Walk blocks in reading order, maintaining a stack of open headings
    keyed by font size (larger size = higher/shallower in the tree)."""
    stack: list[tuple[float, str]] = []
    paths: list[list[str]] = []
    for block in blocks:
        if _is_heading(block, body_size):
            while stack and stack[-1][0] <= block.font_size:
                stack.pop()
            stack.append((block.font_size, block.text))
        paths.append([text for _, text in stack])
    return paths


def _token_count(text: str) -> int:
    return len(_get_encoding().encode(text))


def _merge_bbox(a: list[float], b: tuple[float, float, float, float]) -> list[float]:
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def chunk_document(
    blocks: list[ParsedBlock],
    config: RetrievalConfig,
) -> list[ChunkDraft]:
    """Structure-aware chunking: target ~`chunk_target_tokens` tokens per
    chunk with `chunk_overlap_ratio` overlap, grouped under whatever
    heading path was in effect for the first line of the chunk. Splits
    only ever happen on line boundaries, never mid-sentence-within-a-line.
    """
    if not blocks:
        return []

    body_size = _detect_body_font_size(blocks)
    heading_paths = _assign_heading_paths(blocks, body_size)
    target_tokens = config.chunk_target_tokens
    overlap_tokens = int(target_tokens * config.chunk_overlap_ratio)

    Item = tuple[ParsedBlock, list[str], int]
    window: list[Item] = []
    window_tokens = 0
    drafts: list[ChunkDraft] = []

    def emit(items: list[Item]) -> None:
        if not items:
            return
        content = "\n".join(b.text for b, _, _ in items)
        path = items[0][1]
        prefix = " > ".join(path)
        embedding_text = f"{prefix}\n{content}" if prefix else content

        page_boxes: dict[int, list[float]] = {}
        for b, _, _ in items:
            if b.page_number not in page_boxes:
                page_boxes[b.page_number] = list(b.bbox)
            else:
                page_boxes[b.page_number] = _merge_bbox(page_boxes[b.page_number], b.bbox)

        drafts.append(
            ChunkDraft(
                content=content,
                embedding_text=embedding_text,
                page_number=items[0][0].page_number,
                bbox={
                    "page_boxes": [
                        {"page": page, "bbox": box} for page, box in page_boxes.items()
                    ]
                },
                token_count=sum(t for _, _, t in items),
                chunk_index=len(drafts),
                heading_path=path,
            )
        )

    for block, path in zip(blocks, heading_paths, strict=True):
        tokens = _token_count(block.text)
        window.append((block, path, tokens))
        window_tokens += tokens

        if window_tokens >= target_tokens:
            emit(window)
            tail: list[Item] = []
            tail_tokens = 0
            for item in reversed(window):
                if tail_tokens >= overlap_tokens:
                    break
                tail.insert(0, item)
                tail_tokens += item[2]
            window = tail
            window_tokens = tail_tokens

    emit(window)
    return drafts
