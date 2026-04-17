#!/usr/bin/env python3
"""
Shared runtime configuration for FinServ database and Redis scripts.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv
from redis_mcp.runtime_contract import (
    CASE_ACTIVITY_STREAM_KEY,
    DELINQUENT_ACCOUNTS_KEY,
    PORTFOLIO_HEALTH_KEY,
    SHIFT_NOTES_KEY,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

@dataclass(frozen=True)
class RedisConnectionConfig:
    url: str
    addr: str
    username: str
    password: str
    db: int
    tls_enabled: bool


@dataclass(frozen=True)
class RuntimeConfig:
    database_url: str
    redis_url: str
    redis: RedisConnectionConfig
    redis_fingerprint: str


def _required_env(name: str, *, allow_empty: bool = False) -> str:
    value = os.environ.get(name, "")
    if value or allow_empty:
        return value
    raise RuntimeError(f"{name} is not set. Update .env before running this command.")


def parse_redis_url(redis_url: str) -> RedisConnectionConfig:
    parsed = urlparse(redis_url)
    if parsed.scheme not in {"redis", "rediss"}:
        raise RuntimeError(
            "REDIS_URL must use redis:// or rediss:// and point at the shared Redis Cloud database."
        )
    if not parsed.hostname:
        raise RuntimeError("REDIS_URL is missing a hostname.")

    port = parsed.port or (6380 if parsed.scheme == "rediss" else 6379)
    db = 0
    if parsed.path and parsed.path != "/":
        try:
            db = int(parsed.path.lstrip("/"))
        except ValueError as exc:
            raise RuntimeError("REDIS_URL database path must be an integer.") from exc

    username = unquote(parsed.username) if parsed.username else ""
    password = unquote(parsed.password) if parsed.password else ""

    if password and not username:
        username = "default"

    return RedisConnectionConfig(
        url=redis_url,
        addr=f"{parsed.hostname}:{port}",
        username=username,
        password=password,
        db=db,
        tls_enabled=parsed.scheme == "rediss",
    )


def redis_fingerprint(redis: RedisConnectionConfig) -> str:
    return "|".join(
        [
            redis.addr,
            redis.username,
            str(redis.db),
            "tls" if redis.tls_enabled else "plain",
        ]
    )


def get_runtime_config() -> RuntimeConfig:
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/loanops",
    )
    redis_url = _required_env("REDIS_URL")
    redis = parse_redis_url(redis_url)
    return RuntimeConfig(
        database_url=database_url,
        redis_url=redis_url,
        redis=redis,
        redis_fingerprint=redis_fingerprint(redis),
    )
