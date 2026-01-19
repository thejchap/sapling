from functools import cache
from typing import ClassVar, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

type IsolationLevel = Literal["DEFERRED", "IMMEDIATE", "EXCLUSIVE"] | None


class SaplingSettings(BaseSettings):
    """
    sapling configuration settings.

    all settings can be configured via environment variables with
    the SAPLING_ prefix (e.g., SAPLING_SQLITE_PATH, SAPLING_SQLITE_TIMEOUT).
    """

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="SAPLING_",
    )
    sqlite_path: str = Field(
        default=":memory:",
        description='database file path, or ":memory:" for in-memory',
    )
    sqlite_timeout: float = Field(
        default=5.0,
        description="seconds to wait before raising exception if database is locked",
    )
    sqlite_detect_types: int = Field(
        default=0,
        description="control type detection for non-native sqlite types",
    )
    sqlite_isolation_level: IsolationLevel = Field(
        default="DEFERRED",
        description="transaction isolation: DEFERRED, IMMEDIATE, EXCLUSIVE, or None",
    )
    sqlite_check_same_thread: bool = Field(
        default=False,
        description="if True, only creating thread may use connection",
    )
    sqlite_cached_statements: int = Field(
        default=128,
        description="number of statements to cache internally",
    )
    sqlite_uri: bool = Field(
        default=False,
        description="if True, interpret path as URI with query string",
    )


@cache
def get_sapling_settings() -> SaplingSettings:
    return SaplingSettings()
