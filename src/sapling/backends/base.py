from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from pydantic import BaseModel

    from sapling.database import Document


class Backend(ABC):
    """abstract base class for storage backends."""

    @abstractmethod
    def get[T: BaseModel](
        self, model_class: type[T], model_id: str
    ) -> Document[T] | None: ...

    @abstractmethod
    def put[T: BaseModel](
        self, model_class: type[T], model_id: str, model: T
    ) -> Document[T]: ...

    @abstractmethod
    def fetch[T: BaseModel](
        self, model_class: type[T], model_id: str
    ) -> Document[T]: ...

    @abstractmethod
    def delete(self, model_class: type[BaseModel], model_id: str) -> None: ...

    @abstractmethod
    def all[T: BaseModel](self, model_class: type[T]) -> list[Document[T]]: ...

    @abstractmethod
    def get_many[T: BaseModel](
        self, model_class: type[T], model_ids: list[str]
    ) -> list[Document[T] | None]: ...

    @abstractmethod
    def delete_many(
        self, model_class: type[BaseModel], model_ids: list[str]
    ) -> None: ...

    @abstractmethod
    def put_many[T: BaseModel](
        self, model_class: type[T], models: list[tuple[str, T]]
    ) -> list[Document[T]]: ...

    @abstractmethod
    def initialize(self) -> None: ...

    @abstractmethod
    def transaction(self) -> AbstractContextManager[Self]: ...
