from django.conf import settings
from django.db import connection, reset_queries
import time
import functools
import logging

logger = logging.getLogger("nutrition")


def query_debugger(func):
    @functools.wraps(func)
    def inner_func(*args, **kwargs):
        # Если не DEBUG — просто выполняем функцию
        if not settings.DEBUG:
            return func(*args, **kwargs)

        reset_queries()
        start_queries = len(connection.queries)
        start = time.perf_counter()

        result = func(*args, **kwargs)

        end = time.perf_counter()
        end_queries = len(connection.queries)

        logger.debug("=========== query debugger info ===========")
        logger.debug(f"View (function name): {func.__name__}")
        logger.debug(f"Queries quantity: {end_queries - start_queries}")
        logger.debug(f"Execution time: {(end - start):.2f}s")

        return result

    return inner_func
