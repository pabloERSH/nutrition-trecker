from django.contrib.postgres.search import TrigramWordSimilarity
from django.db.models import Q
from django.db.models.functions import Greatest
from rest_framework.filters import BaseFilterBackend


class FuzzySearchFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        search_query = request.query_params.get("search")
        current_action = getattr(view, "action", None)

        if not search_query:
            return queryset

        if current_action == "autocomplete":
            search_fields = getattr(view, "autocomplete_search_fields", None)
            if not search_fields:
                search_fields = getattr(view, "search_fields", ["name"])

            threshold = 0.1  # Порог для автокомплита
        else:
            search_fields = getattr(view, "search_fields", ["name"])
            threshold = getattr(view, "fuzzy_threshold", 0.3)

        similarities = [
            TrigramWordSimilarity(search_query, field) for field in search_fields
        ]

        if len(similarities) > 1:
            queryset = queryset.annotate(similarity=Greatest(*similarities))
        else:
            queryset = queryset.annotate(similarity=similarities[0])

        filter_condition = Q()
        for field in search_fields:
            filter_condition |= Q(**{f"{field}__icontains": search_query})

        queryset = queryset.filter(filter_condition | Q(similarity__gt=threshold))

        return queryset.order_by("-similarity", "id")
