#!/usr/bin/env python3
"""
Ensure the FinServ RedisVL schema files and RediSearch indices exist.
"""

from __future__ import annotations

import redis

from redis_mcp.indexing import ensure_indices
from runtime_config import get_runtime_config


def connect_redis():
    settings = get_runtime_config()
    return redis.from_url(settings.redis_url, decode_responses=True)


def main() -> None:
    r = connect_redis()
    r.ping()

    print("Ensuring RedisVL-managed RediSearch indices...")
    indices = ensure_indices(r)
    for entity, index in indices.items():
        print(f"  {entity}: {index.name}")

    print("")
    print("RedisVL setup ready.")


if __name__ == "__main__":
    main()
