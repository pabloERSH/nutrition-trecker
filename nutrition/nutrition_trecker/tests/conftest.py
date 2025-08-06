import pytest
import os
from django.db import connection
import logging
from django.conf import settings



logger = logging.getLogger("tests")


# Hooks

def pytest_configure(config):
    """Хук для логирования начала сессии"""
    logger.info("============= Test session starts =============")
    db = settings.DATABASES['default']
    logger.info(f"Test DB: engine={db['ENGINE'].split('.')[-1]}, "
                f"main_db={db['NAME']}, test_db={db['TEST'].get('NAME')}")

# Fixtures

@pytest.fixture(scope='session', autouse=True)
def _django_test_db(request):
    """Гибридный подход: создаём временную БД только в CI"""
    if "django_db" in request.keywords:
        if os.getenv('CI'): # Для CI
            test_db_name = f"pytest_{os.getpid()}"
            logger.info(f"\nCreated temporary test DB: {test_db_name}")
            connection.creation.create_test_db(test_db_name)
            yield
            logger.info(f"\nDeleted temporary test DB: {test_db_name}")
            connection.creation.destroy_test_db(test_db_name)
        else:
            yield
    else:
        yield

@pytest.fixture(autouse=True)
def _clean_tables(request):
    """Очистка таблиц после каждого теста"""
    yield
    if "django_db" in request.keywords:
        if not os.getenv('CI'):  # Для постоянной БД
            logger.info(f"Cleaning test DB {settings.DATABASES['default']['NAME']} after {request.node.name}")
            from django.apps import apps
            for model in apps.get_models():
                model.objects.all().delete()
