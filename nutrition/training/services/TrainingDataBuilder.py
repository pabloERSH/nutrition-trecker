from training.models import TrainingSession
from django.db.models import (
    Count,
    Sum,
    Max,
    F,
    Value,
    DecimalField,
    IntegerField,
    ExpressionWrapper,
)
from django.db.models.functions import Coalesce


class TrainingDataBuilder:
    """Класс для получения данных из моделей training"""

    @classmethod
    def get_training_session_info(cls, training_session: TrainingSession) -> dict:
        """Возвращает полную информацию о тренировке в виде словаря:
        дату, описание, упражнения, подходы, повторения, вес и т.д."""
        # Получаем статистику одним запросом
        stats = (
            TrainingSession.objects.filter(id=training_session.id)
            .annotate(
                # Счётчики
                exercises_count=Count("exercises", distinct=True),
                sets_count=Count("exercises__sets"),
                # Повторения
                total_reps=Coalesce(
                    Sum("exercises__sets__repetitions"),
                    Value(0, output_field=IntegerField()),
                ),
                # Тоннаж
                total_tonnage=Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F("exercises__sets__weight")
                            * F("exercises__sets__repetitions"),
                            output_field=DecimalField(max_digits=12, decimal_places=2),
                        )
                    ),
                    Value(
                        0, output_field=DecimalField(max_digits=12, decimal_places=2)
                    ),
                ),
                # Максимальный вес
                max_weight=Coalesce(
                    Max("exercises__sets__weight"),
                    Value(0, output_field=DecimalField(max_digits=6, decimal_places=2)),
                ),
                # Кардио
                total_duration_seconds=Coalesce(
                    Sum("exercises__sets__duration_seconds"),
                    Value(0, output_field=IntegerField()),
                ),
                total_distance_meters=Coalesce(
                    Sum("exercises__sets__distance_meters"),
                    Value(
                        0, output_field=DecimalField(max_digits=10, decimal_places=2)
                    ),
                ),
                # Отдых
                total_rest_seconds=Coalesce(
                    Sum("exercises__sets__rest_after_set"),
                    Value(0, output_field=IntegerField()),
                ),
            )
            .values(
                "exercises_count",
                "sets_count",
                "total_reps",
                "total_tonnage",
                "max_weight",
                "total_duration_seconds",
                "total_distance_meters",
                "total_rest_seconds",
            )
            .first()
        )

        # Если статистика не найдена (маловероятно)
        if not stats:
            stats = {
                "exercises_count": 0,
                "sets_count": 0,
                "total_reps": 0,
                "total_tonnage": 0.0,
                "max_weight": 0.0,
                "total_duration_seconds": 0,
                "total_distance_meters": 0.0,
                "total_rest_seconds": 0,
            }

        # Расчет производных метрик
        workout_intensity = 0
        if training_session.duration > 0:
            workout_intensity = stats["total_tonnage"] / training_session.duration

        avg_reps_per_set = 0
        if stats["sets_count"] > 0:
            avg_reps_per_set = stats["total_reps"] / stats["sets_count"]

        avg_tonnage_per_set = 0
        if stats["sets_count"] > 0:
            avg_tonnage_per_set = stats["total_tonnage"] / stats["sets_count"]

        # Собираем тренировочные данные
        training_data = {
            "id": training_session.id,
            "user_id": training_session.user_id,
            "name": training_session.name,
            "description": training_session.description or "",
            "date_time": training_session.date_time.isoformat(),
            "date_time_display": training_session.date_time.strftime("%d.%m.%Y %H:%M"),
            "date": training_session.date_time.date().isoformat(),
            "time": training_session.date_time.time().strftime("%H:%M"),
            "duration_minutes": training_session.duration,
            "created_at": (
                training_session.created_at.isoformat()
                if training_session.created_at
                else None
            ),
            "updated_at": (
                training_session.updated_at.isoformat()
                if training_session.updated_at
                else None
            ),
            # Статистика тренировки
            "statistics": {
                "workload": {  # Общая нагрузка (количественные показатели)
                    "exercises": stats["exercises_count"],
                    "sets": stats["sets_count"],
                    "reps": stats["total_reps"],
                    "tonnage": float(stats["total_tonnage"]),
                    "tonnage_display": f"{stats['total_tonnage']:.1f} кг",
                },
                "performance": {  # Показатели интенсивности и весов
                    "max_weight": float(stats["max_weight"]),
                    "max_weight_display": f"{stats['max_weight']:.1f} кг",
                    "avg_reps_per_set": round(float(avg_reps_per_set), 1),
                    "avg_tonnage_per_set": round(float(avg_tonnage_per_set), 1),
                    "intensity_value": round(float(workout_intensity), 1),
                    "intensity_display": f"{workout_intensity:.1f} кг/мин",
                },
                "duration_distance": {  # Те самые метрики времени и пути
                    "duration_seconds": stats["total_duration_seconds"],
                    "duration_display": cls._format_seconds(
                        stats["total_duration_seconds"]
                    ),
                    "distance_meters": float(stats["total_distance_meters"]),
                    "distance_display": f"{stats['total_distance_meters']:.1f} м",
                },
                "rest": {
                    "total_seconds": stats["total_rest_seconds"],
                    "total_display": cls._format_seconds(stats["total_rest_seconds"]),
                    "avg_per_set": cls._format_seconds(
                        stats["total_rest_seconds"] // stats["sets_count"]
                        if stats["sets_count"] > 0
                        else 0
                    ),
                },
            },
        }

        return training_data

    @staticmethod
    def _format_seconds(seconds: int) -> str:
        """Форматирует секунды в читаемый вид"""
        if not seconds:
            return "0:00"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
