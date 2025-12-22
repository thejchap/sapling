from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from sapling.backends.sqlite import SQLiteBackend

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator
    from contextlib import AbstractContextManager
    from types import TracebackType

    from sapling.backends.base import Backend
    from sapling.document import Document


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


class Database:
    """
    main interface for sapling persistence.

    provides crud operations with automatic transaction management.
    delegates to backend implementations for storage.

    Args:
        backend: storage backend (defaults to SQLiteBackend)
        initialize: whether to initialize backend immediately

    Example:
        ```python
        db = Database()
        user = User(name="alice", email="alice@example.com")
        doc = db.put(User, "user_1", user)
        ```

    """

    def __init__(
        self, backend: Backend | None = None, *, initialize: bool = True
    ) -> None:
        self._backend = backend or SQLiteBackend()
        if initialize:
            self._backend.initialize()

    def initialize(self) -> None:
        """
        Initialize backend (idempotent - safe to call multiple times).

        use this when `initialize=False` was passed to Database constructor.
        """
        self._backend.initialize()

    def transaction(self) -> _TransactionWrapper:
        """
        Create transaction context for multiple operations.

        commits on success, rolls back on exception.

        Returns:
            context manager yielding backend instance

        Example:
            ```python
            with db.transaction() as txn:
                txn.put(User, "1", user1)
                txn.put(User, "2", user2)
            ```

        """
        return _TransactionWrapper(self._backend.transaction())

    def transaction_dependency(self) -> Generator[Backend]:
        """
        Fastapi dependency for request-scoped transactions.

        use with Depends() for automatic transaction management.

        Yields:
            backend instance for crud operations

        Example:
            ```python
            @app.post("/users/{user_id}")
            def create(
                user_id: str,
                user: User,
                txn: Annotated[Backend, Depends(db.transaction_dependency)],
            ):
                return txn.put(User, user_id, user)
            ```

        """
        with self._backend.transaction() as txn:
            yield txn

    def get[T: BaseModel](
        self, model_class: type[T], model_id: str
    ) -> Document[T] | None:
        """
        Retrieve document by id, returns None if not found.

        Args:
            model_class: pydantic model class
            model_id: document identifier

        Returns:
            document if found, None otherwise

        """
        with self.transaction() as txn:
            return txn.get(model_class, model_id)

    def put[T: BaseModel](
        self, model_class: type[T], model_id: str, model: T
    ) -> Document[T]:
        """
        Insert or update document.

        Args:
            model_class: pydantic model class
            model_id: document identifier
            model: pydantic model instance

        Returns:
            persisted document

        """
        with self.transaction() as txn:
            return txn.put(model_class, model_id, model)

    def fetch[T: BaseModel](self, model_class: type[T], model_id: str) -> Document[T]:
        """
        Retrieve document by id, raises if not found.

        Args:
            model_class: pydantic model class
            model_id: document identifier

        Returns:
            document

        Raises:
            NotFoundError: document does not exist

        """
        with self.transaction() as txn:
            return txn.fetch(model_class, model_id)

    def delete(self, model_class: type[BaseModel], model_id: str) -> None:
        """
        Delete document by id.

        idempotent - no error if document doesn't exist.

        Args:
            model_class: pydantic model class
            model_id: document identifier

        """
        with self.transaction() as txn:
            return txn.delete(model_class, model_id)

    def all[T: BaseModel](self, model_class: type[T]) -> list[Document[T]]:
        """
        Retrieve all documents of given model class.

        Args:
            model_class: pydantic model class

        Returns:
            list of documents (empty if none exist)

        """
        with self.transaction() as txn:
            return txn.all(model_class)

    def get_many[T: BaseModel](
        self, model_class: type[T], model_ids: list[str]
    ) -> list[Document[T] | None]:
        """
        Retrieve multiple documents by ids, preserving order.

        Args:
            model_class: pydantic model class
            model_ids: list of document identifiers

        Returns:
            list of documents (None for missing ids)

        """
        with self.transaction() as txn:
            return txn.get_many(model_class, model_ids)

    def delete_many(self, model_class: type[BaseModel], model_ids: list[str]) -> None:
        """
        Delete multiple documents by ids.

        idempotent - no error if documents don't exist.

        Args:
            model_class: pydantic model class
            model_ids: list of document identifiers

        """
        with self.transaction() as txn:
            return txn.delete_many(model_class, model_ids)

    def put_many[T: BaseModel](
        self, model_class: type[T], models: list[tuple[str, T]]
    ) -> list[Document[T]]:
        """
        Insert or update multiple documents.

        Args:
            model_class: pydantic model class
            models: list of (model_id, model) tuples

        Returns:
            list of persisted documents

        """
        with self.transaction() as txn:
            return txn.put_many(model_class, models)
