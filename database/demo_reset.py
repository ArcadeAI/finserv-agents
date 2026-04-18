#!/usr/bin/env python3
"""
Clear only the demo workflow state in Redis Cloud.

This leaves entity documents, search indices, and curated Redis views intact.
"""

from __future__ import annotations

import redis

from runtime_config import CASE_ACTIVITY_STREAM_KEY, SHIFT_NOTES_KEY, get_runtime_config


def main() -> None:
    settings = get_runtime_config()
    client = redis.from_url(settings.redis_url, decode_responses=True)
    deleted = client.delete(SHIFT_NOTES_KEY, CASE_ACTIVITY_STREAM_KEY)

    print("Demo workflow state cleared.")
    print(f"  Removed {deleted} key{'s' if deleted != 1 else ''}")
    print(f"  {SHIFT_NOTES_KEY}")
    print(f"  {CASE_ACTIVITY_STREAM_KEY}")


if __name__ == "__main__":
    main()
