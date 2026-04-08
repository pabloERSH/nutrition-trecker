from datetime import datetime, timedelta

from django.utils.timezone import make_aware, is_naive
from rest_framework.filters import BaseFilterBackend


class OneDateFilter(BaseFilterBackend):
    """
    Фильтрация по дате:
    ?date=2026-01-20
    """

    param_name = "date"
    field_name = "date_time"

    def filter_queryset(self, request, queryset, view):
        date_str = request.query_params.get(self.param_name)

        if not date_str:
            return queryset

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            # некорректная дата — просто игнорируем фильтр
            return queryset

        start = datetime.combine(date, datetime.min.time())
        end = start + timedelta(days=1)

        if is_naive(start):
            start = make_aware(start)
            end = make_aware(end)

        return queryset.filter(
            **{
                f"{self.field_name}__gte": start,
                f"{self.field_name}__lt": end,
            }
        )
