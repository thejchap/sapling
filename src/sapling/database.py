from collections.abc import Generator, Iterator
from contextlib import AbstractContextManager
from types import TracebackType

from pydantic import BaseModel
from tryke_guard import __TRYKE_TESTING__

from sapling.backends.base import Backend
from sapling.backends.sqlite import SQLiteBackend
from sapling.document import Document


class _TransactionWrapper:
    """
    Wrapper for backend transactions.

    works as both context managers and generators.
    """

    def __init__(self, backend_transaction_cm: AbstractContextManager[Backend]) -> None:
        self._backend_txn_cm: AbstractContextManager[Backend] = backend_transaction_cm

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

    provides crud operations with transaction management.

    Args:
        backend: storage backend (defaults to SQLiteBackend)
        initialize: whether to initialize backend immediately

    """

    def __init__(
        self, backend: Backend | None = None, *, initialize: bool = True
    ) -> None:
        self._backend: Backend = backend or SQLiteBackend()
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


if __TRYKE_TESTING__:
    from contextlib import contextmanager
    from typing import Annotated

    from fastapi import Depends as FastAPIDepends
    from fastapi import FastAPI, status
    from fastapi.testclient import TestClient
    from tryke import Depends, describe, expect, fixture, test

    from sapling.errors import NotFoundError

    with describe("database"):

        class _TestModel(BaseModel):
            hello: str = "world"

        @fixture
        def database() -> Database:
            return Database()

        @fixture
        def transaction(db: Database = Depends(database)) -> Generator[Backend]:
            with db.transaction() as txn:
                yield txn

        @test
        def test_basic(txn: Backend = Depends(transaction)) -> None:
            hello = _TestModel()
            pk = "hello"
            record = txn.put(_TestModel, pk, hello)
            expect(record.model_id).to_equal(pk)
            maybe_record = txn.get(_TestModel, pk)
            expect(maybe_record).to_be_truthy()
            _record = txn.fetch(_TestModel, pk)
            txn.delete(_TestModel, pk)
            expect(lambda: txn.fetch(_TestModel, pk)).to_raise(NotFoundError)

        @test
        def test_all_method(txn: Backend = Depends(transaction)) -> None:
            txn.put(_TestModel, "1", _TestModel(hello="one"))
            txn.put(_TestModel, "2", _TestModel(hello="two"))
            txn.put(_TestModel, "3", _TestModel(hello="three"))
            all_hellos = txn.all(_TestModel)
            expect(all_hellos).to_have_length(3)
            expect({h.model_id for h in all_hellos}).to_equal({"1", "2", "3"})
            expect({h.model.hello for h in all_hellos}).to_equal(
                {"one", "two", "three"}
            )

        @test
        def test_all_empty(txn: Backend = Depends(transaction)) -> None:
            all_hellos = txn.all(_TestModel)
            expect(all_hellos).to_equal([])

    with describe("initialization"):

        @test
        def test_deferred_initialization() -> None:
            db = Database(backend=SQLiteBackend(), initialize=False)
            db.initialize()
            with db.transaction() as txn:
                txn.put(_TestModel, "test", _TestModel(hello="world"))
                doc = txn.fetch(_TestModel, "test")
                expect(doc.model.hello).to_equal("world")

        @test
        def test_idempotent_initialization() -> None:
            db = Database(backend=SQLiteBackend(), initialize=False)
            db.initialize()
            db.initialize()
            db.initialize()
            with db.transaction() as txn:
                txn.put(_TestModel, "test", _TestModel(hello="world"))

        @test
        def test_uninitialized_error() -> None:
            db = Database(backend=SQLiteBackend(), initialize=False)

            def try_uninitialized() -> None:
                with db.transaction() as txn:
                    txn.put(_TestModel, "test", _TestModel(hello="world"))

            expect(try_uninitialized).to_raise(ValueError, match="not initialized")

    with describe("fastapi"):

        class User(BaseModel):
            name: str
            email: str

        @contextmanager
        def _client() -> Generator[TestClient]:
            app = FastAPI(debug=True)
            db = Database()

            @app.post("/users/{user_id}")
            def create_user(
                user_id: str,
                user: User,
                txn: Annotated[Backend, FastAPIDepends(db.transaction_dependency)],
            ) -> dict:
                doc = txn.put(User, user_id, user)
                return {"id": doc.model_id, "user": doc.model.model_dump()}

            @app.get("/users/{user_id}")
            def get_user(
                user_id: str,
                txn: Annotated[Backend, FastAPIDepends(db.transaction_dependency)],
            ) -> dict:
                doc = txn.fetch(User, user_id)
                return doc.model.model_dump()

            @app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
            def delete_user(
                user_id: str,
                txn: Annotated[Backend, FastAPIDepends(db.transaction_dependency)],
            ) -> None:
                txn.delete(User, user_id)

            @app.get("/users/{user_id}/error")
            def get_user_with_error(
                user_id: str,
                txn: Annotated[Backend, FastAPIDepends(db.transaction_dependency)],
            ) -> dict:
                txn.put(User, user_id, User(name="test", email="test@example.com"))
                raise ValueError

            with TestClient(app, raise_server_exceptions=False) as client:
                yield client

        @test
        def test_create_user() -> None:
            with _client() as client:
                response = client.post(
                    "/users/user1",
                    json={"name": "alice", "email": "alice@example.com"},
                )
                expect(response.status_code).to_equal(status.HTTP_200_OK)
                data = response.json()
                expect(data["id"]).to_equal("user1")
                expect(data["user"]["name"]).to_equal("alice")

        @test
        def test_get_nonexistent_user_raises_not_found() -> None:
            with _client() as client:
                response = client.get("/users/nonexistent")
                expect(response.status_code).to_equal(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        @test
        def test_error_in_route_returns_500() -> None:
            with _client() as client:
                response = client.get("/users/user3/error")
                expect(response.status_code).to_equal(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                )
