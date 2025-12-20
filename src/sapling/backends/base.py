from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from pydantic import BaseModel

    from sapling.database import Document


class Backend(ABC):
    """
    Abstract base class for storage backends.

    backends implement this interface to store documents in different storage systems
    (sqlite, postgres, http apis, filesystems, etc.)
    """

    @abstractmethod
    def get[T: BaseModel](
        self, model_class: type[T], model_id: str
    ) -> Document[T] | None:
        """Get document by id, returns None if not found."""
        ...

    @abstractmethod
    def put[T: BaseModel](
        self, model_class: type[T], model_id: str, model: T
    ) -> Document[T]:
        """Insert or update document."""
        ...

    @abstractmethod
    def fetch[T: BaseModel](self, model_class: type[T], model_id: str) -> Document[T]:
        """Get document by id, raises NotFoundError if not found."""
        ...

    @abstractmethod
    def delete(self, model_class: type[BaseModel], model_id: str) -> None:
        """Delete document by id."""
        ...

    @abstractmethod
    def all[T: BaseModel](self, model_class: type[T]) -> list[Document[T]]:
        """Get all documents of a model class."""
        ...

    @abstractmethod
    def transaction(self) -> AbstractContextManager[Self]:
        """
        Context manager that yields self for transaction operations.

        for sql backends: starts a database transaction
        for http backends: no-op, just yields self
        for filesystem backends: acquires file lock
        """
        ...
