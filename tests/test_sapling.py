from pathlib import Path

import pytest
from pydantic import BaseModel

from sapling import Database, MemoryBackend, SaplingSettings, SQLiteBackend
from sapling.errors import NotFoundError


class Hello(BaseModel):
    hello: str = "world"


def test_basic():
    db = Database()
    hello = Hello()
    with db.transaction() as txn:
        pk = "hello"
        record = txn.put(Hello, pk, hello)
        assert record.model_id == pk
        maybe_record = txn.get(Hello, pk)
        assert maybe_record
        record = txn.fetch(Hello, pk)
        txn.delete(Hello, pk)
        with pytest.raises(NotFoundError):
            txn.fetch(Hello, pk)


def test_all_method():
    db = Database()
    with db.transaction() as txn:
        txn.put(Hello, "1", Hello(hello="one"))
        txn.put(Hello, "2", Hello(hello="two"))
        txn.put(Hello, "3", Hello(hello="three"))

        all_hellos = txn.all(Hello)
        assert len(all_hellos) == 3
        assert {h.model_id for h in all_hellos} == {"1", "2", "3"}
        assert {h.model.hello for h in all_hellos} == {"one", "two", "three"}


def test_all_empty():
    db = Database()
    with db.transaction() as txn:
        all_hellos = txn.all(Hello)
        assert all_hellos == []


def test_sqlite_backend_memory():
    backend = SQLiteBackend()
    db = Database(backend=backend)
    with db.transaction() as txn:
        txn.put(Hello, "test", Hello(hello="world"))
        doc = txn.fetch(Hello, "test")
        assert doc.model.hello == "world"


def test_sqlite_backend_file(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    settings = SaplingSettings(sqlite_path=str(db_path))
    backend = SQLiteBackend(settings=settings)
    db = Database(backend=backend)

    with db.transaction() as txn:
        txn.put(Hello, "persistent", Hello(hello="saved"))

    settings2 = SaplingSettings(sqlite_path=str(db_path))
    db2 = Database(backend=SQLiteBackend(settings=settings2))
    with db2.transaction() as txn:
        doc = txn.fetch(Hello, "persistent")
        assert doc.model.hello == "saved"


def test_backend_all_method():
    backend = SQLiteBackend()
    db = Database(backend=backend)

    with db.transaction() as txn:
        txn.put(Hello, "a", Hello(hello="alpha"))
        txn.put(Hello, "b", Hello(hello="beta"))

        all_docs = txn.all(Hello)
        assert len(all_docs) == 2
        assert {d.model_id for d in all_docs} == {"a", "b"}


def test_memory_backend():
    backend = MemoryBackend()
    db = Database(backend=backend)

    with db.transaction() as txn:
        txn.put(Hello, "test", Hello(hello="world"))
        doc = txn.fetch(Hello, "test")
        assert doc.model.hello == "world"

        txn.put(Hello, "1", Hello(hello="one"))
        txn.put(Hello, "2", Hello(hello="two"))

        all_docs = txn.all(Hello)
        assert len(all_docs) == 3
        assert {d.model_id for d in all_docs} == {"test", "1", "2"}

        txn.delete(Hello, "test")
        assert txn.get(Hello, "test") is None

        with pytest.raises(NotFoundError):
            txn.fetch(Hello, "test")


def test_deferred_initialization():
    backend = SQLiteBackend()
    db = Database(backend=backend, initialize=False)

    db.initialize()

    with db.transaction() as txn:
        txn.put(Hello, "test", Hello(hello="world"))
        doc = txn.fetch(Hello, "test")
        assert doc.model.hello == "world"


def test_idempotent_initialization():
    backend = SQLiteBackend()
    db = Database(backend=backend, initialize=False)

    db.initialize()
    db.initialize()
    db.initialize()

    with db.transaction() as txn:
        txn.put(Hello, "test", Hello(hello="world"))


def test_uninitialized_error():
    backend = SQLiteBackend()
    db = Database(backend=backend, initialize=False)

    with pytest.raises(ValueError, match="not initialized"):  # noqa: SIM117
        with db.transaction() as txn:
            txn.put(Hello, "test", Hello(hello="world"))
