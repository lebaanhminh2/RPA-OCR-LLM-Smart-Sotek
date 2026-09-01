from app.domain.models import Document
from app.domain.ports.repository import Repository


class DocumentNotFoundError(Exception):
    def __init__(self, document_id: str) -> None:
        super().__init__(f"Document not found: {document_id}")


class DocumentService:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    def get_document(self, document_id: str) -> Document:
        document = self._repository.get_document(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)
        return document
