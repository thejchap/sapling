import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

from pydantic import BaseModel


class Transaction:
    def __init__(self, sqlite_transaction: sqlite3.Connection) -> None:
        self._txn = sqlite_transaction

    def insert[T: BaseModel](self, model: T) -> T:
        return model


class Connection:
    def __init__(self, sqlite_connection: sqlite3.Connection) -> None:
        self._conn = sqlite_connection

    @contextmanager
    def transaction(self) -> Generator[Transaction]:
        with self._conn as transaction:
            yield Transaction(sqlite_transaction=transaction)


class Database:
    @contextmanager
    def connection(self) -> Generator[Connection]:
        conn = sqlite3.connect(":memory:")
        try:
            yield Connection(sqlite_connection=conn)
        finally:
            conn.close()
