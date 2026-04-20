from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Self

from tryke_guard import __TRYKE_TESTING__

from sapling.backends.base import Backend
from sapling.document import Document
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

    def get_many[T: BaseModel](
        self, model_class: type[T], model_ids: list[str]
    ) -> list[Document[T] | None]:
        return [self.get(model_class, model_id) for model_id in model_ids]

    def delete_many(self, model_class: type[BaseModel], model_ids: list[str]) -> None:
        for model_id in model_ids:
            self.delete(model_class, model_id)

    def put_many[T: BaseModel](
        self, model_class: type[T], models: list[tuple[str, T]]
    ) -> list[Document[T]]:
        return [self.put(model_class, model_id, model) for model_id, model in models]


if __TRYKE_TESTING__:
    from pydantic import BaseModel as _BaseModel
    from tryke import describe, expect, test

    with describe("memory backend"):

        class _TestModel(_BaseModel):
            hello: str = "world"

        @test
        def test_memory_backend() -> None:
            backend = MemoryBackend()
            backend.initialize()
            with backend.transaction() as txn:
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
