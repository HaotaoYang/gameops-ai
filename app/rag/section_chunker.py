import re
from dataclasses import dataclass

from app.rag.documents import (
    Chunk,
    Document,
    split_document,
)


@dataclass(frozen=True)
class SectionChunk(Chunk):
    """A Chunk with additional section metadata."""

    heading: str = ""


SECTION_PATTERN = re.compile(
    r"^#{2,6}[ \t]+([^\n]+)$",
    re.MULTILINE,
)


def split_by_heading(
    document: Document,
    *,
    chunk_size: int = 180,
    overlap: int = 40,
) -> list[SectionChunk]:
    """Split Markdown by sections, with window fallback."""

    if chunk_size <= 0:
        raise ValueError("chunk_size必须大于0")

    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap必须小于chunk_size且非负")

    text = document.content

    if not text.strip():
        return []

    matches = list(SECTION_PATTERN.finditer(text))

    # Each section is represented by:
    # (heading, start position, end position).
    sections = []

    if not matches:
        sections.append(
            (document.id, 0, len(text))
        )

    else:
        first_start = matches[0].start()

        # Preserve an introduction if it contains real content.
        prefix = text[:first_start]

        prefix_body = re.sub(
            r"^#[ \t]+[^\n]+$",
            "",
            prefix,
            flags=re.MULTILINE,
        )

        if prefix_body.strip():
            sections.append(
                (document.id, 0, first_start)
            )

        for index, match in enumerate(matches):
            start = match.start()

            end = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(text)
            )

            heading = match.group(1).strip()

            sections.append(
                (heading, start, end)
            )

    result = []

    for section_index, section in enumerate(sections):
        heading, start, end = section

        section_document = Document(
            id=f"{document.id}#section-{section_index}",
            source=document.source,
            content=text[start:end],
        )

        # Reuse Day 29 for long sections.
        pieces = split_document(
            section_document,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for piece in pieces:
            result.append(
                SectionChunk(
                    id=piece.id,
                    document_id=document.id,
                    source=document.source,
                    content=piece.content,
                    start=start + piece.start,
                    end=start + piece.end,
                    heading=heading,
                )
            )

    return result


def build_section_chunks(
    documents: list[Document],
    *,
    chunk_size: int = 180,
    overlap: int = 40,
) -> list[SectionChunk]:
    """Build structure-aware chunks for all documents."""

    chunks = []

    for document in documents:
        chunks.extend(
            split_by_heading(
                document,
                chunk_size=chunk_size,
                overlap=overlap,
            )
        )

    return chunks