import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends as FastAPIDepends
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pydantic import BaseModel
from tryke import Depends, describe, expect, fixture, test

from sapling import Database, MemoryBackend, SQLiteBackend
from sapling.backends.base import Backend
from sapling.errors import NotFoundError
from sapling.settings import SaplingSettings

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
        expect({h.model.hello for h in all_hellos}).to_equal({"one", "two", "three"})

    @test
    def test_all_empty(txn: Backend = Depends(transaction)) -> None:
        all_hellos = txn.all(_TestModel)
        expect(all_hellos).to_equal([])

    @test
    def test_backend_all_method() -> None:
        backend = SQLiteBackend()
        db = Database(backend=backend)

        with db.transaction() as txn:
            txn.put(_TestModel, "a", _TestModel(hello="alpha"))
            txn.put(_TestModel, "b", _TestModel(hello="beta"))

            all_docs = txn.all(_TestModel)
            expect(all_docs).to_have_length(2)
            expect({d.model_id for d in all_docs}).to_equal({"a", "b"})

    @test
    def test_memory_backend() -> None:
        backend = MemoryBackend()
        db = Database(backend=backend)

        with db.transaction() as txn:
            txn.put(_TestModel, "test", _TestModel(hello="world"))
            doc = txn.fetch(_TestModel, "test")
            expect(doc.model.hello).to_equal("world")

            txn.put(_TestModel, "1", _TestModel(hello="one"))
            txn.put(_TestModel, "2", _TestModel(hello="two"))

            all_docs = txn.all(_TestModel)
            expect(all_docs).to_have_length(3)
            expect({d.model_id for d in all_docs}).to_equal({"test", "1", "2"})

            txn.delete(_TestModel, "test")
            expect(txn.get(_TestModel, "test")).to_be_none()

            expect(lambda: txn.fetch(_TestModel, "test")).to_raise(NotFoundError)


with describe("sqlite"):

    @test
    def test_sqlite_backend_memory() -> None:
        backend = SQLiteBackend()
        db = Database(backend=backend)
        with db.transaction() as txn:
            txn.put(_TestModel, "test", _TestModel(hello="world"))
            doc = txn.fetch(_TestModel, "test")
            expect(doc.model.hello).to_equal("world")

    @test
    def test_sqlite_backend_file() -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "test.db"
            settings = SaplingSettings(sqlite_path=str(db_path))
            backend = SQLiteBackend(settings=settings)
            db = Database(backend=backend)

            with db.transaction() as txn:
                txn.put(_TestModel, "persistent", _TestModel(hello="saved"))

            settings2 = SaplingSettings(sqlite_path=str(db_path))
            db2 = Database(backend=SQLiteBackend(settings=settings2))
            with db2.transaction() as txn:
                doc = txn.fetch(_TestModel, "persistent")
                expect(doc.model.hello).to_equal("saved")


with describe("initialization"):

    @test
    def test_deferred_initialization() -> None:
        backend = SQLiteBackend()
        db = Database(backend=backend, initialize=False)

        db.initialize()

        with db.transaction() as txn:
            txn.put(_TestModel, "test", _TestModel(hello="world"))
            doc = txn.fetch(_TestModel, "test")
            expect(doc.model.hello).to_equal("world")

    @test
    def test_idempotent_initialization() -> None:
        backend = SQLiteBackend()
        db = Database(backend=backend, initialize=False)

        db.initialize()
        db.initialize()
        db.initialize()

        with db.transaction() as txn:
            txn.put(_TestModel, "test", _TestModel(hello="world"))

    @test
    def test_uninitialized_error() -> None:
        backend = SQLiteBackend()
        db = Database(backend=backend, initialize=False)

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
    def test_create_user():
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
    def test_get_nonexistent_user_raises_not_found():
        with _client() as client:
            response = client.get("/users/nonexistent")
            expect(response.status_code).to_equal(status.HTTP_500_INTERNAL_SERVER_ERROR)

    @test
    def test_error_in_route_returns_500():
        with _client() as client:
            response = client.get("/users/user3/error")
            expect(response.status_code).to_equal(status.HTTP_500_INTERNAL_SERVER_ERROR)
