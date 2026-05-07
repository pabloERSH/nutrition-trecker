from .settings import *  # noqa: F403
import os

# Переопределяем БД для тестов
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("TEST_DB", "test_db"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
        "HOST": os.getenv("TEST_DB_HOST", "localhost"),
        "PORT": os.getenv("TEST_DB_PORT", "5432"),
    }
}

# Заменяем Redis на локальный кэш
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}
