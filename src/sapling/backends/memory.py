from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Self

from sapling.backends.base import Backend
from sapling.database import Document
from sapling.errors import NotFoundError

if TYPE_CHECKING:
    from collections.abc import Generator

    from pydantic import BaseModel


class MemoryBackend(Backend):
    """
    in-memory storage backend.

    stores documents in python dict, no persistence.
    useful for testing and development.

    Example:
        ```python
        backend = MemoryBackend()
        db = Database(backend=backend)
        ```

    """

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], dict] = {}

    def initialize(self) -> None:
        pass

    @contextmanager
    def transaction(self) -> Generator[Self]:
        yield self

    def get[T: BaseModel](
        self, model_class: type[T], model_id: str
    ) -> Document[T] | None:
        key = (model_class.__name__, model_id)
        if data := self._store.get(key):
            model = model_class.model_validate(data["model"])
            return Document(
                model=model,
                model_id=data["model_id"],
                model_class=data["model_class"],
            )
        return None

    def put[T: BaseModel](
        self, model_class: type[T], model_id: str, model: T
    ) -> Document[T]:
        key = (model_class.__name__, model_id)
        data = {
            "model_class": model_class.__name__,
            "model_id": model_id,
            "model": model.model_dump(),
        }
        self._store[key] = data
        return Document(
            model=model,
            model_id=model_id,
            model_class=model_class.__name__,
        )

    def fetch[T: BaseModel](self, model_class: type[T], model_id: str) -> Document[T]:
        if document := self.get(model_class=model_class, model_id=model_id):
            return document
        raise NotFoundError

    def delete(self, model_class: type[BaseModel], model_id: str) -> None:
        key = (model_class.__name__, model_id)
        self._store.pop(key, None)

    def all[T: BaseModel](self, model_class: type[T]) -> list[Document[T]]:
        results = []
        for (stored_class, _), data in self._store.items():
            if stored_class == model_class.__name__:
                model = model_class.model_validate(data["model"])
                results.append(
                    Document(
                        model=model,
                        model_id=data["model_id"],
                        model_class=data["model_class"],
                    )
                )
        return results
