import pytest
from pydantic import BaseModel
from ulid import ULID

from sapling import Database
from sapling.errors import NotFoundError


class Hello(BaseModel):
    hello: str = "world"


def test_basic():
    db = Database()
    hello = Hello()
    with db.connection() as conn, conn.transaction() as txn:
        pk = str(ULID())
        record = txn.put(Hello, pk, hello)
        assert record.model_id == pk
        maybe_record = txn.get(Hello, pk)
        assert maybe_record
        record = txn.fetch(Hello, pk)
        txn.delete(Hello, pk)
        with pytest.raises(NotFoundError):
            txn.fetch(Hello, pk)
