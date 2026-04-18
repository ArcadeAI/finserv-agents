#!/usr/bin/env python3
"""
Flush the configured live Redis database and remove FinServ search indices.

This is intentionally destructive:
- matching FinServ RediSearch indices are dropped directly from Redis.
- `FLUSHDB` clears every key in the Redis database selected by REDIS_URL.
"""

from __future__ import annotations

import redis

from redis_mcp.indexing import INDEX_SPECS, list_search_indices
from runtime_config import get_runtime_config


def _matching_index_names(client: redis.Redis) -> list[str]:
    suffixes = {spec.legacy_suffix for spec in INDEX_SPECS.values()}
    preferred = {spec.index_name for spec in INDEX_SPECS.values()}

    matches: list[str] = []
    for name in list_search_indices(client):
        if name in preferred or any(name.endswith(f":{suffix}") for suffix in suffixes):
            matches.append(name)
    return sorted(set(matches))


def delete_search_indices(client: redis.Redis) -> tuple[list[str], list[str]]:
    deleted: list[str] = []
    failed: list[str] = []

    for name in _matching_index_names(client):
        try:
            client.execute_command("FT.DROPINDEX", name)
            deleted.append(name)
            print(f"Dropped search index: {name}")
        except Exception as exc:  # noqa: BLE001
            failed.append(name)
            print(f"Failed to drop search index {name}: {exc}")

    return deleted, failed


def flush_redis_db(client: redis.Redis) -> None:
    settings = get_runtime_config()
    before = client.dbsize()
    client.flushdb()
    after = client.dbsize()
    print(f"Flushed Redis DB {settings.redis.db}: {before} keys removed, {after} remaining.")


def main() -> None:
    settings = get_runtime_config()
    client = redis.from_url(settings.redis_url, decode_responses=True)

    print("Resetting live Redis and RediSearch state...")
    deleted, failed = delete_search_indices(client)
    if failed:
        print("")
        print("Search index cleanup was incomplete.")
        print(f"  Failed deletions: {', '.join(failed)}")
        raise SystemExit(1)

    if deleted:
        print("")
        print("Search index cleanup finished.")
    else:
        print("No matching FinServ search indices found.")

    print("Flushing Redis DB...")
    flush_redis_db(client)


if __name__ == "__main__":
    main()
