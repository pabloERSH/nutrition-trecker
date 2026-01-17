from functools import wraps
from rest_framework.response import Response
from django.core.cache import cache
from common.utils.CacheKeyBuilder import CacheKeyBuilder


def cache_response(*, entity: str, ttl: int, per_user=False):
    def decorator(view_method):
        @wraps(view_method)
        def wrapper(self, request, *args, **kwargs):
            user_id = request.user.telegram_id if per_user else "global"

            builder = CacheKeyBuilder(
                entity=entity,
                user_id=user_id,
            )

            if "pk" in kwargs:
                cache_key = builder.build(
                    scope="detail",
                    extra={"pk": kwargs["pk"]},
                )
            else:
                filters = {
                    k: request.query_params.getlist(k)
                    for k in getattr(self, "filterset_fields", [])
                    if k in request.query_params
                }

                cache_key = builder.build(
                    scope="list",
                    filters=filters,
                    page=request.query_params.get("page"),
                )

            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

            response = view_method(self, request, *args, **kwargs)

            if isinstance(response, Response):
                cache.set(cache_key, response.data, ttl)

            return response

        return wrapper

    return decorator
