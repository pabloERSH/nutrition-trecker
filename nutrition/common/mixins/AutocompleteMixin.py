from rest_framework.decorators import action
from rest_framework.response import Response


class AutocompleteMixin:
    autocomplete_search_fields = ["name"]
    autocomplete_min_length = 2
    autocomplete_limit = 10

    @action(detail=False, methods=["get"])
    def autocomplete(self, request):
        search = request.query_params.get("search", "")
        if len(search) < self.autocomplete_min_length:
            return Response([])

        queryset = self.filter_queryset(self.get_queryset())

        data = queryset.values(*self.autocomplete_search_fields)[
            : self.autocomplete_limit
        ]
        return Response(list(data))
