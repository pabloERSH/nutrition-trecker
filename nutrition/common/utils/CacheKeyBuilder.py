import json
import hashlib
from .CacheHelper import CacheHelper


def serialize_cache_payload(payload: dict) -> str:
    """
    Делает стабильную строку из payload:
    - сортирует ключи
    - хэширует (ключи не раздуваются)
    """
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


class CacheKeyBuilder:
    def __init__(self, *, entity: str, user_id="global"):
        self.entity = entity
        self.user_id = user_id

    def build(self, *, scope: str, filters=None, page=None, extra=None) -> str:
        payload = {
            "scope": scope,
            "filters": filters or {},
            "page": page,
            "extra": extra,
        }

        suffix = serialize_cache_payload(payload)

        return CacheHelper.make_cache_key(
            self.entity,
            suffix,
            self.user_id,
        )
