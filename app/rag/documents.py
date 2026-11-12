from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Document:
    """One original knowledge-base document."""

    id: str
    source: str
    content: str


@dataclass(frozen=True)
class Chunk:
    """One searchable piece of a document."""

    id: str
    document_id: str
    source: str
    content: str
    start: int
    end: int


def load_documents(directory: Path) -> list[Document]:
    """Load Markdown documents from a local directory."""

    if not directory.is_dir():
        raise ValueError(
            f"知识库目录不存在：{directory}"
        )

    documents = []

    for path in sorted(directory.glob("*.md")):
        content = path.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            continue

        documents.append(
            Document(
                id=path.stem,
                source=path.name,
                content=content,
            )
        )

    return documents


def split_document(
    document: Document,
    *,
    chunk_size: int = 180,
    overlap: int = 40,
) -> list[Chunk]:
    """Split a document into overlapping character windows."""

    if chunk_size <= 0:
        raise ValueError("chunk_size必须大于0")

    if not 0 <= overlap < chunk_size:
        raise ValueError(
            "overlap必须大于等于0且小于chunk_size"
        )

    content = document.content

    if not content:
        return []

    chunks = []
    start = 0
    index = 0

    while start < len(content):
        end = min(
            start + chunk_size,
            len(content),
        )

        chunks.append(
            Chunk(
                id=f"{document.id}#chunk-{index}",
                document_id=document.id,
                source=document.source,
                content=content[start:end],
                start=start,
                end=end,
            )
        )

        if end == len(content):
            break

        start = end - overlap
        index += 1

    return chunks


def build_chunks(
    documents: list[Document],
    *,
    chunk_size: int = 180,
    overlap: int = 40,
) -> list[Chunk]:
    """Build searchable chunks from all documents."""

    chunks = []

    for document in documents:
        chunks.extend(
            split_document(
                document,
                chunk_size=chunk_size,
                overlap=overlap,
            )
        )

    return chunks