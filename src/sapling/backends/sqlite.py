from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel

from sapling.backends.base import Backend
from sapling.database import Document
from sapling.errors import NotFoundError

if TYPE_CHECKING:
    from collections.abc import Generator

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

_CONNECTION_NOT_INITIALIZED = "Connection not initialized"


class SQLiteBackend(Backend):
    """sqlite backend - stores documents in sqlite database."""

    def __init__(self, path: str = ":memory:") -> None:
        self.path = path
        self._conn: sqlite3.Connection | None = None

    @contextmanager
    def transaction(self) -> Generator[Self]:
        """Open connection, start transaction, yield self."""
        if not self._conn:
            self._conn = sqlite3.connect(self.path)
            self._init_schema()

        with self._conn:
            yield self

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        if self._conn is None:
            raise ValueError(_CONNECTION_NOT_INITIALIZED)
        self._conn.set_trace_callback(LOGGER.debug)
        with self._conn:
            self._conn.execute(
                """\
CREATE TABLE IF NOT EXISTS document (
    model_class VARCHAR,
    model_id CHARACTER(26),
    model BLOB,
    PRIMARY KEY (model_class, model_id)
);
""".strip()
            )

    def _row_to_document[T: BaseModel](
        self, model_class: type[T], cursor: sqlite3.Cursor, row: tuple[Any]
    ) -> Document[T]:
        """Convert sqlite row to Document."""
        fields = [column[0] for column in cursor.description]
        raw = dict(zip(fields, row, strict=False))
        model = model_class.model_validate_json(raw["model"])
        return Document(
            model=model,
            model_id=raw["model_id"],
            model_class=raw["model_class"],
        )

    def get[T: BaseModel](
        self, model_class: type[T], model_id: str
    ) -> Document[T] | None:
        if self._conn is None:
            raise ValueError(_CONNECTION_NOT_INITIALIZED)
        cursor = self._conn.execute(
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
        row = cursor.fetchone()
        if row:
            return self._row_to_document(model_class, cursor, row)
        return None

    def put[T: BaseModel](
        self, model_class: type[T], model_id: str, model: T
    ) -> Document[T]:
        if self._conn is None:
            raise ValueError(_CONNECTION_NOT_INITIALIZED)
        cursor = self._conn.execute(
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
        row = cursor.fetchone()
        return self._row_to_document(model_class, cursor, row)

    def fetch[T: BaseModel](self, model_class: type[T], model_id: str) -> Document[T]:
        if document := self.get(model_class=model_class, model_id=model_id):
            return document
        raise NotFoundError

    def delete(self, model_class: type[BaseModel], model_id: str) -> None:
        if self._conn is None:
            raise ValueError(_CONNECTION_NOT_INITIALIZED)
        self._conn.execute(
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

    def all[T: BaseModel](self, model_class: type[T]) -> list[Document[T]]:
        if self._conn is None:
            raise ValueError(_CONNECTION_NOT_INITIALIZED)
        cursor = self._conn.execute(
            """\
SELECT
    model_class,
    model_id,
    model
FROM document
WHERE
    model_class = :model_class
;
            """.strip(),
            {"model_class": model_class.__name__},
        )
        return [
            self._row_to_document(model_class, cursor, row) for row in cursor.fetchall()
        ]
