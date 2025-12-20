from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Document[T: BaseModel](BaseModel):
    """
    container for persisted pydantic models.

    documents wrap model data with persistence metadata, keeping pydantic
    models pure (no database-specific fields).

    Attributes:
        model: the pydantic model instance
        model_id: unique identifier
        model_class: fully qualified model class name

    Example:
        ```python
        user = User(name="alice", email="alice@example.com")
        doc = txn.put(User, "user_1", user)
        print(doc.model_id)  # "user_1"
        print(doc.model.name)  # "alice"
        ```

    """

    model_config = ConfigDict(frozen=True)
    model: T
    model_id: str
    model_class: str
