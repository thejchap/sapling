from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator
    from contextlib import AbstractContextManager
    from types import TracebackType

    from sapling.backends.base import Backend


class _TransactionWrapper:
    """
    Wrapper for backend transactions.

    works as both context managers and generators.
    """

    def __init__(self, backend_transaction_cm: AbstractContextManager[Backend]) -> None:
        self._backend_txn_cm = backend_transaction_cm

    def __enter__(self) -> Backend:
        return self._backend_txn_cm.__enter__()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        return self._backend_txn_cm.__exit__(exc_type, exc_value, traceback)

    def __call__(self) -> Iterator[Backend]:
        return iter(self)

    def __iter__(self) -> Generator[Backend]:
        with self._backend_txn_cm as txn:
            yield txn


class Document[T: BaseModel](BaseModel):
    """
    pure data container for persisted models.

    documents contain model data, model type, and model id
    no backend-specific logic - backends handle document creation
    """

    model_config = ConfigDict(frozen=True)
    model: T
    model_id: str
    model_class: str


class Database:
    """
    database - thin wrapper that delegates to backends.

    provides convenient api for crud operations with automatic transactions
    """

    def __init__(self, backend: Backend | None = None) -> None:
        from sapling.backends.sqlite import SQLiteBackend  # noqa: PLC0415

        self._backend = backend if backend is not None else SQLiteBackend()

    def transaction(self) -> _TransactionWrapper:
        """
        Context manager for multi-operation transactions.

        use with `with db.transaction() as txn:`
        yields the backend instance for direct crud operations
        commits on success, rolls back on exception

        for fastapi, use transaction_dependency() instead
        """
        return _TransactionWrapper(self._backend.transaction())

    def transaction_dependency(self) -> Generator[Backend]:
        """
        Yield backend transaction for fastapi dependency injection.

        use with `Depends(db.transaction_dependency)`
        yields the backend instance for direct crud operations
        """
        with self._backend.transaction() as txn:
            yield txn

    def get[T: BaseModel](
        self, model_class: type[T], model_id: str
    ) -> Document[T] | None:
        """Get document by id (auto-transaction)."""
        with self.transaction() as txn:
            return txn.get(model_class, model_id)

    def put[T: BaseModel](
        self, model_class: type[T], model_id: str, model: T
    ) -> Document[T]:
        """Insert or update document (auto-transaction)."""
        with self.transaction() as txn:
            return txn.put(model_class, model_id, model)

    def fetch[T: BaseModel](self, model_class: type[T], model_id: str) -> Document[T]:
        """Get document by id, raises NotFoundError if not found (auto-transaction)."""
        with self.transaction() as txn:
            return txn.fetch(model_class, model_id)

    def delete(self, model_class: type[BaseModel], model_id: str) -> None:
        """Delete document by id (auto-transaction)."""
        with self.transaction() as txn:
            return txn.delete(model_class, model_id)

    def all[T: BaseModel](self, model_class: type[T]) -> list[Document[T]]:
        """Get all documents of a model class (auto-transaction)."""
        with self.transaction() as txn:
            return txn.all(model_class)
