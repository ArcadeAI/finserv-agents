from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import redis as redis_lib
from redisvl.index import SearchIndex
from redisvl.schema import IndexSchema

BORROWER_ENTITY = "borrower"
LOAN_ENTITY = "loan"
PAYMENT_ENTITY = "payment"
FRAUD_SIGNAL_ENTITY = "fraudsignal"


@dataclass(frozen=True)
class IndexSpec:
    entity: str
    index_name: str
    schema_file: str
    key_prefix: str
    legacy_suffix: str
    id_field: str
    related_field: str | None = None

    @property
    def redis_key_prefix(self) -> str:
        return f"{self.key_prefix}:"


INDEX_SPECS: dict[str, IndexSpec] = {
    BORROWER_ENTITY: IndexSpec(
        entity=BORROWER_ENTITY,
        index_name="idx:finserv:borrower",
        schema_file="borrower.yaml",
        key_prefix="finserv:borrower",
        legacy_suffix="borrower",
        id_field="borrower_id",
    ),
    LOAN_ENTITY: IndexSpec(
        entity=LOAN_ENTITY,
        index_name="idx:finserv:loan",
        schema_file="loan.yaml",
        key_prefix="finserv:loan",
        legacy_suffix="loan",
        id_field="loan_id",
        related_field="borrower_id",
    ),
    PAYMENT_ENTITY: IndexSpec(
        entity=PAYMENT_ENTITY,
        index_name="idx:finserv:payment",
        schema_file="payment.yaml",
        key_prefix="finserv:payment",
        legacy_suffix="payment",
        id_field="payment_id",
        related_field="borrower_id",
    ),
    FRAUD_SIGNAL_ENTITY: IndexSpec(
        entity=FRAUD_SIGNAL_ENTITY,
        index_name="idx:finserv:fraudsignal",
        schema_file="fraudsignal.yaml",
        key_prefix="finserv:fraud_signal",
        legacy_suffix="fraudsignal",
        id_field="signal_id",
        related_field="borrower_id",
    ),
}

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"


def index_spec(entity: str) -> IndexSpec:
    try:
        return INDEX_SPECS[entity]
    except KeyError as exc:
        raise KeyError(f"Unknown RedisVL entity '{entity}'.") from exc


def schema_path(entity: str) -> Path:
    return SCHEMA_DIR / index_spec(entity).schema_file


def load_index_schema(entity: str) -> IndexSchema:
    path = schema_path(entity)
    if not path.exists():
        raise FileNotFoundError(
            f"RedisVL schema file is missing for '{entity}': {path}"
        )
    return IndexSchema.from_yaml(str(path))


def entity_key(entity: str, record_id: str) -> str:
    spec = index_spec(entity)
    return f"{spec.key_prefix}:{record_id}"


def list_search_indices(redis_client: redis_lib.Redis) -> list[str]:
    return [str(name) for name in redis_client.execute_command("FT._LIST")]


def _pair_list_to_dict(values: list[Any]) -> dict[str, Any]:
    return {
        str(values[index]): values[index + 1]
        for index in range(0, len(values), 2)
        if index + 1 < len(values)
    }


def _ft_info(redis_client: redis_lib.Redis, index_name: str) -> dict[str, Any]:
    raw = redis_client.execute_command("FT.INFO", index_name)
    return _pair_list_to_dict(raw)


def _live_key_count(redis_client: redis_lib.Redis, spec: IndexSpec) -> int:
    count = 0
    for _ in redis_client.scan_iter(match=f"{spec.redis_key_prefix}*", count=1000):
        count += 1
    return count


def _index_doc_count(redis_client: redis_lib.Redis, index_name: str) -> int:
    info = _ft_info(redis_client, index_name)
    return int(info.get("num_docs", 0))


def native_index_is_ready(
    redis_client: redis_lib.Redis,
    entity: str,
) -> bool:
    spec = index_spec(entity)
    available = set(list_search_indices(redis_client))
    if spec.index_name not in available:
        return False

    try:
        return _index_doc_count(redis_client, spec.index_name) >= _live_key_count(
            redis_client,
            spec,
        )
    except Exception:
        return False


def discover_index_name(
    redis_client: redis_lib.Redis,
    entity: str,
) -> str | None:
    spec = index_spec(entity)
    available = set(list_search_indices(redis_client))

    if spec.index_name in available and native_index_is_ready(redis_client, entity):
        return spec.index_name

    for name in sorted(available):
        if name != spec.index_name and name.endswith(f":{spec.legacy_suffix}"):
            return name

    if spec.index_name in available:
        return spec.index_name

    return None


def load_search_index(
    redis_client: redis_lib.Redis,
    entity: str,
) -> SearchIndex:
    existing_name = discover_index_name(redis_client, entity)
    schema = load_index_schema(entity)
    if existing_name:
        schema.index.name = existing_name
    return SearchIndex(schema=schema, redis_client=redis_client)


def ensure_index(redis_client: redis_lib.Redis, entity: str) -> SearchIndex:
    index = SearchIndex.from_yaml(str(schema_path(entity)), redis_client=redis_client)
    index.create(overwrite=False)
    return index


def ensure_indices(redis_client: redis_lib.Redis) -> dict[str, SearchIndex]:
    return {
        entity: ensure_index(redis_client, entity)
        for entity in INDEX_SPECS
    }
