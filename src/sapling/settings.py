from functools import cache
from typing import ClassVar, Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

type IsolationLevel = Literal["DEFERRED", "IMMEDIATE", "EXCLUSIVE"] | None


class SQLiteSettings(BaseModel):
    path: str = ":memory:"
    timeout: float = 5.0
    detect_types: int = 0
    isolation_level: IsolationLevel = "DEFERRED"
    check_same_thread: bool = False
    cached_statements: int = 128
    uri: bool = False


class SaplingSettings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="SAPLING_",
        env_nested_delimiter="_",
    )
    sqlite: SQLiteSettings = SQLiteSettings()


@cache
def get_sapling_settings() -> SaplingSettings:
    return SaplingSettings()
