from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel, ConfigDict

from sapling.errors import NotFoundError

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from types import TracebackType

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class Document[T: BaseModel](BaseModel):
    """
    A Document is a persisted model.

    Documents contain model data, model type, and model id
    """

    model_config = ConfigDict(frozen=True)
    model: T
    model_id: str
    model_class: str

    @classmethod
    def row_factory(
        cls,
        model_class: type[T],
    ) -> Callable[..., Document[T]]:
        """
        Create a `row_factory` for a given model type.

        https://docs.python.org/3/library/sqlite3.html#how-to-create-and-use-row-factories
        """

        def factory(cursor: sqlite3.Cursor, row: tuple[Any]) -> Document[T]:
            fields = [column[0] for column in cursor.description]
            raw = dict(zip(fields, row, strict=False))
            model = model_class.model_validate_json(raw.pop("model"))
            return cls(
                model=model,
                model_class=raw["model_class"],
                model_id=raw["model_id"],
            )

        return factory


@dataclass(frozen=True, kw_only=True)
class Index[T: BaseModel]:
    model_class: type[T]

    def get_all(self, _value: str) -> list[Document[T]]:
        return []


@dataclass(frozen=True, kw_only=True)
class Transaction:
    sqlite3_transaction: sqlite3.Connection

    def put[T: BaseModel](
        self,
        model_class: type[T],
        model_id: str,
        model: T,
    ) -> Document[T]:
        conn = self.sqlite3_transaction
        conn.row_factory = Document[T].row_factory(model_class)
        res = conn.execute(
            """\
INSERT INTO document VALUES (
    :model_class,
    :model_id,
    :model
) RETURNING
    model_class,
    model_id,
    model
;
            """.strip(),
            {
                "model_class": model_class.__name__,
                "model_id": model_id,
                "model": model.model_dump_json(),
            },
        )
        return res.fetchone()

    def get[T: BaseModel](
        self,
        model_class: type[T],
        model_id: str,
    ) -> Document[T] | None:
        conn = self.sqlite3_transaction
        conn.row_factory = Document[T].row_factory(model_class=model_class)
        res = conn.execute(
            """\
SELECT
    model_class,
    model_id,
    model
FROM document
WHERE
    model_class = :model_class
    AND model_id = :model_id
LIMIT 1
;
            """.strip(),
            {"model_class": model_class.__name__, "model_id": str(model_id)},
        )
        return res.fetchone()

    def fetch[T: BaseModel](self, model_class: type[T], model_id: str) -> Document[T]:
        if document := self.get(model_class=model_class, model_id=model_id):
            return document
        raise NotFoundError

    def delete(self, model_class: type[BaseModel], model_id: str) -> None:
        conn = self.sqlite3_transaction
        conn.execute(
            """\
DELETE
FROM document
WHERE
    model_class = :model_class
    AND model_id = :model_id
;
            """.strip(),
            {"model_class": model_class.__name__, "model_id": str(model_id)},
        )

    def index[T: BaseModel](self, model_class: type[T]) -> Index[T]:
        return Index(model_class=model_class)


class Connection:
    """
    Wrapper around a sqlite3 connection.

    See: https://docs.python.org/3/library/sqlite3.html
    """

    sqlite3_connection: sqlite3.Connection

    @contextmanager
    def transaction(self) -> Generator[Transaction]:
        if not self.sqlite3_connection:
            raise ValueError
        with self.sqlite3_connection as transaction:
            yield Transaction(sqlite3_transaction=transaction)

    def __enter__(self) -> Self:
        """TODO."""
        self.sqlite3_connection = sqlite3.connect(":memory:")
        self._initdb()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        """TODO."""
        self.sqlite3_connection.close()

    def _initdb(self) -> None:
        conn = self.sqlite3_connection
        conn.set_trace_callback(LOGGER.debug)
        with conn:
            conn.execute(
                """\
CREATE TABLE IF NOT EXISTS document (
    model_class VARCHAR,
    model_id CHARACTER(26),
    model BLOB,
    PRIMARY KEY (model_class, model_id)
);
""".strip()
            )


class Database:
    @contextmanager
    def connection(self) -> Generator[Connection]:
        with Connection() as conn:
            yield conn
