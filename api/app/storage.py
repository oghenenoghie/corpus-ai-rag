from pathlib import Path
from uuid import UUID

# Local disk storage — fine for a single-instance demo deploy, but this is
# the thing to swap for real object storage (S3/R2) before running
# multiple API instances or anything production-grade behind a load balancer.
_STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"


def _path_for(document_id: UUID) -> Path:
    return _STORAGE_DIR / f"{document_id}.pdf"


def save_document_file(document_id: UUID, content: bytes) -> str:
    _STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    path = _path_for(document_id)
    path.write_bytes(content)
    return str(path)


def document_file_path(document_id: UUID) -> Path:
    return _path_for(document_id)
