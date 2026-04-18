from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import redis as redis_lib
from redisvl.index import SearchIndex
from redisvl.query import BaseQuery, CountQuery, FilterQuery
from redisvl.query.filter import Tag

from redis_mcp.indexing import (
    BORROWER_ENTITY,
    FRAUD_SIGNAL_ENTITY,
    LOAN_ENTITY,
    PAYMENT_ENTITY,
    entity_key,
    index_spec,
    load_search_index,
)


def _pick_best_borrower(
    records: list[dict[str, Any]],
    borrower_name: str,
) -> dict[str, Any] | None:
    if not records:
        return None

    target = borrower_name.strip().lower()
    for record in records:
        for field in ("full_name", "company_name"):
            value = record.get(field)
            if isinstance(value, str) and value.strip().lower() == target:
                return record

    for record in records:
        name = str(record.get("full_name", "")).lower()
        company = str(record.get("company_name", "")).lower()
        if target in name or target in company:
            return record

    return records[0]


class RedisVLContextGateway:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis = redis_lib.from_url(redis_url, decode_responses=True)
        self._indices: dict[str, SearchIndex] = {}

    def _index(self, entity: str) -> SearchIndex:
        if entity not in self._indices:
            self._indices[entity] = load_search_index(self.redis, entity)
        return self._indices[entity]

    def _read_json_key(self, key: str) -> dict[str, Any] | None:
        data = self.redis.json().get(key, "$")
        if not data:
            return None
        payload = data[0] if isinstance(data, list) else data
        if not isinstance(payload, dict):
            return None
        return payload

    def _normalize_text_result(self, row: dict[str, Any]) -> dict[str, Any] | None:
        doc_id = row.get("id")
        if not isinstance(doc_id, str) or not doc_id:
            return None

        payload = row.get("json")
        if isinstance(payload, str):
            decoded = json.loads(payload)
            if isinstance(decoded, dict):
                normalized = {"id": doc_id, **decoded}
                if (
                    doc_id.startswith(index_spec(BORROWER_ENTITY).redis_key_prefix)
                    and "borrower_id" not in normalized
                ):
                    normalized["borrower_id"] = doc_id.rsplit(":", 1)[-1]
                return normalized
        if isinstance(payload, dict):
            normalized = {"id": doc_id, **payload}
            if (
                doc_id.startswith(index_spec(BORROWER_ENTITY).redis_key_prefix)
                and "borrower_id" not in normalized
            ):
                normalized["borrower_id"] = doc_id.rsplit(":", 1)[-1]
            return normalized
        return None

    def _normalize_filter_result(self, row: dict[str, Any]) -> dict[str, Any] | None:
        doc_id = row.get("id")
        if not isinstance(doc_id, str) or not doc_id:
            return None
        return row

    def _search_borrowers(
        self,
        borrower_name: str,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        query = BaseQuery(borrower_name.strip() or "*")
        query.paging(0, limit).dialect(2)
        rows = self._index(BORROWER_ENTITY).query(query)
        results: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            normalized = self._normalize_text_result(row)
            if not normalized:
                continue
            if not normalized["id"].startswith(index_spec(BORROWER_ENTITY).redis_key_prefix):
                continue
            results.append(normalized)
        return results

    def _filter_related_records(
        self,
        entity: str,
        borrower_id: str,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        spec = index_spec(entity)
        if not spec.related_field:
            return []

        filter_expression = Tag(spec.related_field) == borrower_id
        index = self._index(entity)

        total_matches = index.query(CountQuery(filter_expression=filter_expression))
        if not isinstance(total_matches, int):
            raise RuntimeError(
                f"Unexpected count result for entity '{entity}': {total_matches!r}"
            )

        rows = index.query(
            FilterQuery(
                filter_expression=filter_expression,
                num_results=max(limit, total_matches),
            )
        )

        results: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            normalized = self._normalize_filter_result(row)
            if not normalized:
                continue
            if not normalized["id"].startswith(spec.redis_key_prefix):
                continue
            results.append(normalized)
        return results[:limit]

    def borrower_snapshot(
        self,
        borrower_name: str,
        *,
        borrower_limit: int = 10,
        loan_limit: int = 50,
        payment_limit: int = 250,
        fraud_limit: int = 50,
    ) -> dict[str, Any]:
        try:
            borrower_candidates = self._search_borrowers(
                borrower_name,
                limit=borrower_limit,
            )
            borrower = _pick_best_borrower(borrower_candidates, borrower_name)
            if not borrower:
                return {
                    "borrower": None,
                    "loans": [],
                    "payments": [],
                    "fraud_signals": [],
                }

            borrower_id = borrower.get("borrower_id")
            if not isinstance(borrower_id, str) or not borrower_id:
                return {
                    "borrower": borrower,
                    "loans": [],
                    "payments": [],
                    "fraud_signals": [],
                }

            borrower_key = entity_key(BORROWER_ENTITY, borrower_id)
            borrower_doc = self._read_json_key(borrower_key) or borrower
            borrower_doc = {"id": borrower_key, "borrower_id": borrower_id, **borrower_doc}

            return {
                "borrower": borrower_doc,
                "loans": self._filter_related_records(
                    LOAN_ENTITY,
                    borrower_id,
                    limit=loan_limit,
                ),
                "payments": self._filter_related_records(
                    PAYMENT_ENTITY,
                    borrower_id,
                    limit=payment_limit,
                ),
                "fraud_signals": self._filter_related_records(
                    FRAUD_SIGNAL_ENTITY,
                    borrower_id,
                    limit=fraud_limit,
                ),
            }
        except (redis_lib.RedisError, ValueError) as exc:
            raise RuntimeError(f"RedisVL borrower lookup failed: {exc}") from exc


@lru_cache(maxsize=8)
def get_redisvl_gateway(redis_url: str) -> RedisVLContextGateway:
    return RedisVLContextGateway(redis_url)
