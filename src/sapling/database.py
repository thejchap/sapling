import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Self

from pydantic import BaseModel, ConfigDict, Field
from ulid import ULID


class Document[T: BaseModel](BaseModel):
    model_config = ConfigDict(frozen=True)
    model: T
    id_: ULID = Field(default_factory=ULID)


@dataclass(kw_only=True)
class Query[T: BaseModel]:
    model_class: type[T]

    def where(self) -> Self:
        return self

    def all(self) -> list[Document[T]]:
        return []


@dataclass(frozen=True, kw_only=True)
class Transaction:
    sqlite_transaction: sqlite3.Connection

    def create[T: BaseModel](self, model: T) -> Document[T]:
        return Document(model=model)

    def get[T: BaseModel](self, model_class: type[T], id_: ULID) -> Document[T] | None:
        return None

    def fetch[T: BaseModel](self, model_class: type[T], id_: ULID) -> Document[T]:
        if document := self.get(model_class=model_class, id_=id_):
            return document
        raise ValueError

    def query[T: BaseModel](self, model_class: type[T]) -> Query[T]:
        return Query(model_class=model_class)


@dataclass(frozen=True, kw_only=True)
class Connection:
    sqlite_connection: sqlite3.Connection

    @contextmanager
    def transaction(self) -> Generator[Transaction]:
        with self.sqlite_connection as transaction:
            yield Transaction(sqlite_transaction=transaction)


@dataclass(frozen=True, kw_only=True)
class Database:
    @contextmanager
    def connection(self) -> Generator[Connection]:
        conn = sqlite3.connect(":memory:")
        try:
            yield Connection(sqlite_connection=conn)
        finally:
            conn.close()
