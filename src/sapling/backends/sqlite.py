from __future__ import annotations

import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self, override

from pydantic import BaseModel

from sapling.backends.base import Backend
from sapling.document import Document
from sapling.errors import NotFoundError
from sapling.settings import IsolationLevel, SaplingSettings, get_sapling_settings

if TYPE_CHECKING:
    from collections.abc import Generator

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

_CONNECTION_NOT_INITIALIZED = "Connection not initialized"


class SQLiteBackend(Backend):
    """
    sqlite-based storage backend.

    provides persistent storage using sqlite database.
    supports both file-based and in-memory modes.

    Args:
        settings: sapling settings instance. if not provided, uses global settings
            from environment variables.

    Example:
        ```python
        # use global settings from environment
        backend = SQLiteBackend()

        # use custom settings
        from sapling import SaplingSettings

        settings = SaplingSettings(
            sqlite_path="/path/to/db.sqlite",
            sqlite_timeout=10.0,
        )
        backend = SQLiteBackend(settings=settings)
        ```

    """

    def __init__(self, settings: SaplingSettings | None = None) -> None:
        settings = settings if settings is not None else get_sapling_settings()
        self.path: str = settings.sqlite_path
        self.timeout: float = settings.sqlite_timeout
        self.detect_types: int = settings.sqlite_detect_types
        self.isolation_level: IsolationLevel = settings.sqlite_isolation_level
        self.check_same_thread: bool = settings.sqlite_check_same_thread
        self.cached_statements: int = settings.sqlite_cached_statements
        self.uri: bool = settings.sqlite_uri
        self._conn: sqlite3.Connection | None = None
        self._initialized: bool = False
        self._init_lock: threading.Lock = threading.Lock()

    @override
    def initialize(self) -> None:
        with self._init_lock:
            if self._initialized:
                return
            if self.path != ":memory:":
                db_dir = Path(self.path).parent
                db_dir.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(
                self.path,
                timeout=self.timeout,
                detect_types=self.detect_types,
                isolation_level=self.isolation_level,
                check_same_thread=self.check_same_thread,
                cached_statements=self.cached_statements,
                uri=self.uri,
            )
            self._init_schema()
            self._initialized = True

    @contextmanager
    def transaction(self) -> Generator[Self]:
        if not self._conn:
            raise ValueError(_CONNECTION_NOT_INITIALIZED)
        with self._conn:
            yield self

    def _init_schema(self) -> None:
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
INSERT OR REPLACE INTO document VALUES (
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

    def get_many[T: BaseModel](
        self, model_class: type[T], model_ids: list[str]
    ) -> list[Document[T] | None]:
        if not model_ids:
            return []
        if self._conn is None:
            raise ValueError(_CONNECTION_NOT_INITIALIZED)
        placeholders = ",".join("?" * len(model_ids))
        cursor = self._conn.execute(
            f"""\
SELECT
    model_class,
    model_id,
    model
FROM document
WHERE
    model_class = ?
    AND model_id IN ({placeholders})
;
            """.strip(),
            [model_class.__name__, *model_ids],
        )
        results_dict = {
            row[1]: self._row_to_document(model_class, cursor, row)
            for row in cursor.fetchall()
        }
        return [results_dict.get(model_id) for model_id in model_ids]

    def delete_many(self, model_class: type[BaseModel], model_ids: list[str]) -> None:
        if not model_ids:
            return
        if self._conn is None:
            raise ValueError(_CONNECTION_NOT_INITIALIZED)
        placeholders = ",".join("?" * len(model_ids))
        self._conn.execute(
            f"""\
DELETE
FROM document
WHERE
    model_class = ?
    AND model_id IN ({placeholders})
;
            """.strip(),
            [model_class.__name__, *model_ids],
        )

    def put_many[T: BaseModel](
        self, model_class: type[T], models: list[tuple[str, T]]
    ) -> list[Document[T]]:
        if not models:
            return []
        if self._conn is None:
            raise ValueError(_CONNECTION_NOT_INITIALIZED)
        values_placeholders = ",".join("(?, ?, ?)" * len(models))
        flat_values = [
            val
            for model_id, model in models
            for val in (model_class.__name__, model_id, model.model_dump_json())
        ]
        cursor = self._conn.execute(
            f"""\
INSERT OR REPLACE INTO document VALUES {values_placeholders}
RETURNING model_class, model_id, model
;
            """.strip(),
            flat_values,
        )
        return [
            self._row_to_document(model_class, cursor, row) for row in cursor.fetchall()
        ]
