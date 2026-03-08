from collections.abc import Generator
from contextlib import contextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, status
from fastapi.testclient import TestClient
from pydantic import BaseModel
from tryke import expect, test

from sapling import Database
from sapling.backends.base import Backend


class User(BaseModel):
    name: str
    email: str


@contextmanager
def _client() -> Generator[TestClient]:
    app = FastAPI(debug=True)
    db = Database()

    @app.post("/users/{user_id}")
    def create_user(
        user_id: str,
        user: User,
        txn: Annotated[Backend, Depends(db.transaction_dependency)],
    ) -> dict:
        doc = txn.put(User, user_id, user)
        return {"id": doc.model_id, "user": doc.model.model_dump()}

    @app.get("/users/{user_id}")
    def get_user(
        user_id: str, txn: Annotated[Backend, Depends(db.transaction_dependency)]
    ) -> dict:
        doc = txn.fetch(User, user_id)
        return doc.model.model_dump()

    @app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_user(
        user_id: str, txn: Annotated[Backend, Depends(db.transaction_dependency)]
    ) -> None:
        txn.delete(User, user_id)

    @app.get("/users/{user_id}/error")
    def get_user_with_error(
        user_id: str, txn: Annotated[Backend, Depends(db.transaction_dependency)]
    ) -> dict:
        txn.put(User, user_id, User(name="test", email="test@example.com"))
        raise ValueError

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@test
def test_create_user():
    with _client() as client:
        response = client.post(
            "/users/user1",
            json={"name": "alice", "email": "alice@example.com"},
        )
        expect(response.status_code).to_equal(status.HTTP_200_OK)
        data = response.json()
        expect(data["id"]).to_equal("user1")
        expect(data["user"]["name"]).to_equal("alice")


@test
def test_get_nonexistent_user_raises_not_found():
    with _client() as client:
        response = client.get("/users/nonexistent")
        expect(response.status_code).to_equal(status.HTTP_500_INTERNAL_SERVER_ERROR)


@test
def test_error_in_route_returns_500():
    with _client() as client:
        response = client.get("/users/user3/error")
        expect(response.status_code).to_equal(status.HTTP_500_INTERNAL_SERVER_ERROR)
