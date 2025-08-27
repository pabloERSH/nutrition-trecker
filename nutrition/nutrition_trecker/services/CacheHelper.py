from django.core.cache import cache


class CacheHelper:
    @classmethod
    def get_cache_version(cls, entity: str, user_id: int | str = "gloabal") -> int:
        version_key = f"cache_version:{entity}:{user_id}"
        version = cache.get(version_key)
        if version is None:
            version = 1
            cache.set(version_key, version, None)
            return version
        return version

    @classmethod
    def bump_cache_version(cls, entity: str, user_id: int | str = "gloabal") -> int:
        version_key = f"cache_version:{entity}:{user_id}"
        cache.incr(version_key)

    @classmethod
    def make_cache_key(
        cls, entity: str, suffix: str, user_id: int | str = "gloabal"
    ) -> str:
        version = cls.get_cache_version(entity, user_id)
        return f"{entity}:{user_id}:v{version}:{suffix}"
