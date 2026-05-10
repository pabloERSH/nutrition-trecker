from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from .models import UserProfile
from .serializers import UserProfileSerializer
from .services.ReportService import WeeklyReportService, WeeklyReportConfig
import logging

logger = logging.getLogger(__name__)


class UserProfileDetailView(generics.RetrieveUpdateAPIView):
    """Получение и обновление профиля пользователя (существующий эндпоинт)"""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(
            user_id=self.request.user.telegram_id
        )
        return profile

    def perform_update(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)


# ====================================================================
# НОВЫЙ ЭНДПОИНТ ДЛЯ AI-АНАЛИЗА
# ====================================================================


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def weekly_report_view(request):
    """
    GET /api/v1/profiles/report/weekly/

    Формирует агрегированный недельный отчёт по питанию и тренировкам
    для последующей передачи в AI Analyzer Service.

    Query Parameters:
        period_days (int, optional)         — глубина анализа в днях.
                                             Минимум 3, максимум 31.
                                             По умолчанию: 7.
        end_date (str, optional)            — последний день периода в формате YYYY-MM-DD.
                                             По умолчанию: сегодня.
        include_previous_week (bool)        — добавить сравнение с предыдущим периодом.
                                             По умолчанию: true.
        include_meals_detail (bool)         — детализация каждого приёма пищи по дням.
                                             По умолчанию: false.
        include_exercises_detail (bool)     — детализация каждого упражнения в тренировках.
                                             По умолчанию: false.

    Returns:
        200: JSON-отчёт (структура — см. WeeklyReportService.build_report)
        400: Недостаточно данных (минимум 3 дня с записями о питании)
        422: Ошибка валидации параметров

    Примеры:
        # Базовый вызов (неделя до сегодня)
        GET /api/v1/profiles/report/weekly/

        # Конкретная неделя с детализацией
        GET /api/v1/profiles/report/weekly/?end_date=2026-04-27&include_meals_detail=true

        # Две недели без сравнения с предыдущим периодом
        GET /api/v1/profiles/report/weekly/?period_days=14&include_previous_week=false
    """

    # 1. Получаем telegram_id из аутентифицированного пользователя
    telegram_id = request.user.telegram_id

    # 2. Парсим и валидируем параметры запроса
    params = _parse_weekly_report_params(request)

    # 3. Формируем конфигурацию отчёта
    config = WeeklyReportConfig(
        user_id=telegram_id,
        end_date=params["end_date"],
        period_days=params["period_days"],
        include_previous_week=params["include_previous_week"],
        include_meals_detail=params["include_meals_detail"],
        include_exercises_detail=params["include_exercises_detail"],
    )

    # 4. Строим отчёт
    service = WeeklyReportService(config)
    report = service.build_report()

    # 5. Проверяем качество данных (адаптировано под новую структуру)
    nutrition = report.get("nutrition", {})
    training = report.get("training", {})

    nutrition_days = nutrition.get("days_logged", 0)
    training_days = training.get("training_days", 0)

    # Проверяем достаточность данных (минимум 3 дня питания)
    if nutrition_days < 3:
        raise ValidationError(
            {
                "detail": "Недостаточно данных для анализа",
                "data_quality": {
                    "nutrition_days_count": nutrition_days,
                    "training_days_count": training_days,
                    "sufficient_data": False,
                },
                "min_required_days": 3,
                "hint": (
                    f"У вас {nutrition_days} дн. с питанием. "
                    f"Добавьте ещё {3 - nutrition_days} дн. записей."
                ),
            }
        )

    # 6. Логируем
    period = report.get("period", {})
    logger.info(
        "Weekly report generated | "
        f"user_id={telegram_id} | "
        f"period={period.get('start', '?')}..{period.get('end', '?')} | "
        f"nutrition_days={nutrition_days} | "
        f"training_days={training_days}",
    )

    return Response(report)


# ====================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ====================================================================


def _parse_weekly_report_params(request) -> dict:
    """
    Парсинг и валидация query-параметров для weekly_report_view.

    Допустимые параметры:
        - period_days: int, 3..31 (по умолчанию 7)
        - end_date: str в формате YYYY-MM-DD (по умолчанию None → today)
        - include_previous_week: bool (по умолчанию True)
        - include_meals_detail: bool (по умолчанию False)
        - include_exercises_detail: bool (по умолчанию False)
    """
    from datetime import datetime

    params = {
        "period_days": 7,
        "end_date": None,
        "include_previous_week": True,
        "include_meals_detail": False,
        "include_exercises_detail": False,
    }

    # --- period_days (целое число, 3..31) ---
    period_days_str = request.query_params.get("period_days")
    if period_days_str is not None:
        try:
            period_days = int(period_days_str)
        except ValueError:
            raise ValidationError({"period_days": "Должен быть целым числом"})

        if period_days < 3:
            raise ValidationError({"period_days": "Минимальный период — 3 дня"})
        if period_days > 31:
            raise ValidationError({"period_days": "Максимальный период — 31 день"})

        params["period_days"] = period_days

    # --- end_date (дата в формате YYYY-MM-DD) ---
    end_date_str = request.query_params.get("end_date")
    if end_date_str is not None:
        try:
            params["end_date"] = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError({"end_date": "Формат даты: YYYY-MM-DD"})

    # --- Булевы флаги (true/false, 1/0, yes/no) ---
    bool_params = [
        "include_previous_week",
        "include_meals_detail",
        "include_exercises_detail",
    ]

    for param_name in bool_params:
        value = request.query_params.get(param_name)
        if value is not None:
            params[param_name] = _parse_bool_param(value, param_name)

    return params


def _parse_bool_param(value: str, param_name: str) -> bool:
    """
    Преобразует строковый параметр в булево значение.

    True:  "true", "1", "yes" (регистронезависимо)
    False: "false", "0", "no"

    Выбрасывает ValidationError при некорректном значении.
    """
    value_lower = value.lower()

    if value_lower in ("true", "1", "yes"):
        return True
    elif value_lower in ("false", "0", "no"):
        return False

    raise ValidationError(
        {
            param_name: (
                f"Недопустимое значение '{value}'. "
                f"Ожидается: true/false, 1/0, yes/no."
            )
        }
    )
