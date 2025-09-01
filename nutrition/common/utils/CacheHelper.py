from django.core.cache import cache


class CacheHelper:
    @classmethod
    def get_cache_version(cls, entity: str, user_id: int | str = "global") -> int:
        """Возвращает текущую версию кэша для выбранной сущности."""
        version_key = f"cache_version:{entity}:{user_id}"
        version = cache.get(version_key)
        if version is None:
            version = 1
            cache.set(version_key, version, None)
            return version
        return version

    @classmethod
    def bump_cache_version(cls, entity: str, user_id: int | str = "global") -> int:
        """Инвалидирует кэш икриментом версии."""
        version_key = f"cache_version:{entity}:{user_id}"
        v = cls.get_cache_version(entity, user_id)
        cache.set(version_key, v + 1)

    @classmethod
    def make_cache_key(
        cls, entity: str, suffix: str, user_id: int | str = "global"
    ) -> str:
        """Возвращает ключ с актуальной версией для создания и нахождения требуемого кэша."""
        version = cls.get_cache_version(entity, user_id)
        return f"{entity}:{user_id}:v{version}:{suffix}"
