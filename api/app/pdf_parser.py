from dataclasses import dataclass

import fitz  # pymupdf

_BOLD_FLAG = 1 << 4  # pymupdf span flag bit for bold


@dataclass
class ParsedBlock:
    """One line of text as it appears on the page, kept small so the
    chunker can group/split at line granularity without ever needing to
    split a line mid-sentence."""

    text: str
    page_number: int  # 1-indexed
    bbox: tuple[float, float, float, float]
    font_size: float
    is_bold: bool


@dataclass
class ParsedDocument:
    blocks: list[ParsedBlock]
    page_count: int


def parse_pdf(content: bytes) -> ParsedDocument:
    """Extract text lines with page numbers, bounding boxes, and font
    metadata (used by the chunker to detect headings)."""
    doc = fitz.open(stream=content, filetype="pdf")
    try:
        blocks: list[ParsedBlock] = []
        for page_index in range(len(doc)):
            page = doc[page_index]
            raw = page.get_text("dict")
            for block in raw["blocks"]:
                if block.get("type") != 0:  # 0 = text, skip images/vector art
                    continue
                for line in block["lines"]:
                    text = "".join(span["text"] for span in line["spans"]).strip()
                    if not text:
                        continue
                    sizes = [span["size"] for span in line["spans"]]
                    bold = any(span["flags"] & _BOLD_FLAG for span in line["spans"])
                    blocks.append(
                        ParsedBlock(
                            text=text,
                            page_number=page_index + 1,
                            bbox=tuple(line["bbox"]),
                            font_size=max(sizes),
                            is_bold=bold,
                        )
                    )
        return ParsedDocument(blocks=blocks, page_count=len(doc))
    finally:
        doc.close()
