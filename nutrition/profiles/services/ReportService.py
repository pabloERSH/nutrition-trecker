from django.utils import timezone
from datetime import date, timedelta
from typing import Optional, List
from dataclasses import dataclass

from nutrition_trecker.models import EatenFood
from nutrition_trecker.services.FoodDataBuilder import FoodDataBuilder
from training.models import TrainingSession
from training.services.TrainingDataBuilder import TrainingDataBuilder
from profiles.models import UserProfile

import logging

logger = logging.getLogger(__name__)


# Коэффициенты для упражнений с собственным весом (доля от веса тела)
BODYWEIGHT_EXERCISE_COEFFICIENTS = {
    # Подтягивания: ~90-95% веса тела
    "PULL_UPS": 0.92,
    "CHIN_UPS": 0.90,
    "WIDE_GRIP_PULL_UPS": 0.92,
    "LAT_PULLDOWN": 0.85,  # Тяга верхнего блока (если без веса)
    # Отжимания: ~60-75% веса тела
    "PUSH_UPS": 0.65,
    "DIAMOND_PUSH_UPS": 0.70,
    "WIDE_PUSH_UPS": 0.60,
    "DECLINE_PUSH_UPS": 0.75,
    "INCLINE_PUSH_UPS": 0.50,
    # Приседания с собственным весом
    "BODYWEIGHT_SQUATS": 0.80,
    "PISTOL_SQUATS": 0.95,
    "JUMP_SQUATS": 0.90,
    # Выпады
    "LUNGES": 0.70,
    "WALKING_LUNGES": 0.75,
    "BULGARIAN_SPLIT_SQUATS": 0.85,
    "REVERSE_LUNGES": 0.70,
    # Пресс/кор
    "LEG_RAISES": 0.40,
    "HANGING_LEG_RAISES": 0.55,
    "PLANK": 0.30,
    "SIDE_PLANK": 0.25,
    "CRUNCHES": 0.35,
    "RUSSIAN_TWISTS": 0.35,
    # Плиометрика
    "BOX_JUMPS": 1.0,
    "BURPEES": 0.85,
    "JUMPING_LUNGES": 0.90,
    "TUCK_JUMPS": 0.95,
    # Разное
    "DIPS": 0.90,  # Отжимания на брусьях
    "BENCH_DIPS": 0.80,
    "GLUTE_BRIDGE": 0.50,
    "HIP_THRUST": 0.60,
    "CALF_RAISES": 0.60,
    "SUPERMANS": 0.20,
    "BIRD_DOG": 0.15,
    # Дефолт для неизвестных bodyweight упражнений
    "DEFAULT_BODYWEIGHT": 0.60,
}

# Кардио: конвертация времени в эквивалентный объём (кг/мин)
CARDIO_VOLUME_EQUIVALENT = {
    "RUNNING": 50,
    "SPRINTING": 80,
    "JOGGING": 35,
    "CYCLING": 35,
    "STATIONARY_BIKE": 30,
    "SWIMMING": 60,
    "JUMP_ROPE": 55,
    "ROWING": 45,
    "ELLIPTICAL": 35,
    "STAIR_CLIMBER": 50,
    "WALKING": 20,
    "DEFAULT_CARDIO": 40,
}


@dataclass
class WeeklyReportConfig:
    """Конфигурация для формирования недельного отчёта"""

    user_id: int
    end_date: Optional[date] = None
    period_days: int = 7
    include_previous_week: bool = True
    include_meals_detail: bool = False
    include_exercises_detail: bool = False


class WeeklyReportService:
    """
    Сервис для формирования агрегированного недельного отчёта,
    оптимизированного для анализа LLM.

    Учитывает:
    - Силовые упражнения с весом (weight × reps)
    - Упражнения с собственным весом (bodyweight % × reps)
    - Кардио (время × коэффициент)
    - Плиометрику (explosive bodyweight)
    """

    MAJOR_MUSCLE_GROUPS = {
        "CHEST",
        "BACK",
        "QUADS",
        "HAMSTRINGS",
        "GLUTES",
        "SHOULDERS",
        "BICEPS",
        "TRICEPS",
    }

    DAY_NAMES = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"}
    MACROS = ["calories", "proteins", "fats", "carbs"]
    MACRO_KEY_MAP = {
        "kcal": "calories",
        "proteins": "proteins",
        "fats": "fats",
        "carbohydrates": "carbs",
    }

    def __init__(self, config: WeeklyReportConfig):
        self.config = config
        self.user_id = config.user_id
        self.end_date = config.end_date or timezone.now().date()
        self.start_date = self.end_date - timedelta(days=config.period_days - 1)
        self.previous_start_date = self.start_date - timedelta(days=config.period_days)
        self.previous_end_date = self.start_date - timedelta(days=1)
        self._profile = None

    def build_report(self) -> dict:
        """Главный метод — сборка компактного отчёта для LLM"""
        logger.info(f"Building LLM-optimized report for user_id={self.user_id}")

        profile = self._get_profile()
        nutrition_data = self._get_nutrition_raw()
        training_sessions = self._get_training_sessions()

        report = {
            "period": {
                "start": self.start_date.isoformat(),
                "end": self.end_date.isoformat(),
                "days": self.config.period_days,
            },
            "user": self._build_user_section(profile),
            "nutrition": self._build_nutrition_section(nutrition_data, profile),
            "training": self._build_training_section(training_sessions),
        }

        report["summary"] = self._generate_summary(report)
        return report

    # ============ ПРОФИЛЬ ============

    def _get_profile(self) -> Optional[UserProfile]:
        if self._profile is None:
            try:
                self._profile = UserProfile.objects.get(user_id=self.user_id)
            except UserProfile.DoesNotExist:
                self._profile = None
        return self._profile

    def _build_user_section(self, profile: Optional[UserProfile]) -> dict:
        if not profile:
            return {
                "setup_complete": False,
                "note": "Профиль не заполнен. Невозможно рассчитать целевые показатели.",
            }

        user = {
            "age": profile.age,
            "gender": dict(UserProfile.GENDER_CHOICES).get(profile.gender, "—"),
            "weight_kg": float(profile.weight) if profile.weight else None,
        }

        if profile.height:
            user["height_cm"] = profile.height
        if profile.body_fat:
            user["body_fat_percent"] = float(profile.body_fat)

        targets = {
            "calories": profile.target_calories,
            "protein_g": profile.target_proteins,
            "fat_g": profile.target_fats,
            "carbs_g": profile.target_carbs,
        }

        if any(v > 0 for v in targets.values()):
            user["targets"] = targets
            user["goal_type"] = dict(UserProfile.GOAL_CHOICES).get(
                profile.goal_type, "Поддержание"
            )
            user["activity"] = dict(UserProfile.ACTIVITY_CHOICES).get(
                profile.activity_level, "Не указан"
            )
        else:
            user["targets_note"] = "Целевые показатели не рассчитаны"

        return user

    # ============ ПИТАНИЕ (без изменений) ============

    def _get_nutrition_raw(self) -> List[dict]:
        queryset = EatenFood.objects.filter(
            user_id=self.user_id,
            eaten_at__date__range=(self.start_date, self.end_date),
        )

        daily_totals = FoodDataBuilder._eaten_food_range_days_total_list_build(
            queryset, self.start_date, self.end_date
        )

        days = []
        current = self.start_date
        while current <= self.end_date:
            key = current.isoformat()
            data = daily_totals.get(key, {})

            if data:
                days.append(
                    {
                        "date": key,
                        "weekday": self.DAY_NAMES[current.weekday()],
                        "calories": data["kcal"],
                        "proteins": data["proteins"],
                        "fats": data["fats"],
                        "carbs": data["carbohydrates"],
                    }
                )
            current += timedelta(days=1)

        return days

    def _build_nutrition_section(
        self, days: List[dict], profile: Optional[UserProfile]
    ) -> dict:
        if not days:
            return {
                "data_available": False,
                "message": "Нет данных о питании за период",
            }

        days_count = len(days)
        totals = {macro: sum(d[macro] for d in days) for macro in self.MACROS}
        averages = {macro: round(totals[macro] / days_count) for macro in self.MACROS}

        protein_per_kg = None
        if profile and profile.weight:
            protein_per_kg = round(averages["proteins"] / float(profile.weight), 1)

        section = {"days_logged": days_count, "averages": averages}

        if protein_per_kg is not None:
            section["protein_per_kg"] = protein_per_kg

        if profile and profile.target_calories > 0:
            section["target_compliance"] = self._calc_compliance(averages, profile)

        section["patterns"] = self._analyze_patterns(days)
        section["alerts"] = self._build_nutrition_alerts(days, averages, profile)

        if self.config.include_previous_week:
            trends = self._get_nutrition_trends(averages)
            if trends:
                section["vs_previous_week"] = trends

        if self.config.include_meals_detail:
            section["daily_data"] = days

        return section

    def _calc_compliance(self, averages: dict, profile: UserProfile) -> dict:
        compliance = {}
        targets = {
            "calories": profile.target_calories,
            "proteins": profile.target_proteins,
            "fats": profile.target_fats,
            "carbs": profile.target_carbs,
        }

        for macro, target in targets.items():
            if target > 0 and macro in averages:
                pct = round(averages[macro] / target * 100)
                compliance[macro] = {
                    "actual": averages[macro],
                    "target": target,
                    "percent": pct,
                    "status": (
                        "good" if 85 <= pct <= 115 else "low" if pct < 85 else "high"
                    ),
                }

        return compliance if compliance else None

    def _analyze_patterns(self, days: List[dict]) -> dict:
        patterns = {}

        if len(days) < 3:
            patterns["note"] = "Недостаточно дней для анализа паттернов"
            return patterns

        best = max(days, key=lambda d: d["calories"])
        worst = min(days, key=lambda d: d["calories"])

        patterns["best_day"] = (
            f"{best['weekday']} ({best['date']}): {best['calories']:.0f} ккал"
        )
        patterns["worst_day"] = (
            f"{worst['weekday']} ({worst['date']}): {worst['calories']:.0f} ккал"
        )

        cals = [d["calories"] for d in days]
        avg_cal = sum(cals) / len(cals)
        if avg_cal > 0:
            spread = (max(cals) - min(cals)) / avg_cal * 100
            patterns["consistency"] = {
                "min_kcal": min(cals),
                "max_kcal": max(cals),
                "spread_percent": round(spread),
                "verdict": (
                    "стабильно"
                    if spread < 30
                    else (
                        "умеренные колебания"
                        if spread < 60
                        else "сильная нестабильность"
                    )
                ),
            }

        weekday_cals = [d["calories"] for d in days if d["weekday"] not in ("Сб", "Вс")]
        weekend_cals = [d["calories"] for d in days if d["weekday"] in ("Сб", "Вс")]

        if weekday_cals and weekend_cals:
            wd_avg = sum(weekday_cals) / len(weekday_cals)
            we_avg = sum(weekend_cals) / len(weekend_cals)
            diff_pct = round((we_avg - wd_avg) / wd_avg * 100)

            patterns["weekday_vs_weekend"] = {
                "weekday_avg": round(wd_avg),
                "weekend_avg": round(we_avg),
                "difference_percent": diff_pct,
                "note": (
                    "в выходные ест больше"
                    if diff_pct > 15
                    else (
                        "в выходные ест меньше"
                        if diff_pct < -15
                        else "ровное потребление"
                    )
                ),
            }

        return patterns

    def _build_nutrition_alerts(
        self, days: List[dict], averages: dict, profile: Optional[UserProfile]
    ) -> List[dict]:
        alerts = []

        if not profile or profile.target_calories == 0:
            alerts.append(
                {
                    "severity": "warning",
                    "message": "Не заданы целевые показатели. Заполните профиль для персонализированных рекомендаций.",
                    "action": "settings",
                }
            )
            return alerts

        cal_pct = averages["calories"] / profile.target_calories * 100

        if cal_pct < 40:
            alerts.append(
                {
                    "severity": "critical",
                    "message": f"Критический недобор: {averages['calories']} из {profile.target_calories} ккал ({cal_pct:.0f}%). Риск потери мышечной массы.",
                    "action": f"Добавьте {profile.target_calories - averages['calories']:.0f} ккал/день. Начните с +500 ккал.",
                }
            )
        elif cal_pct < 70:
            alerts.append(
                {
                    "severity": "warning",
                    "message": f"Значительный недобор калорий: {cal_pct:.0f}% от нормы.",
                    "action": "Добавьте 1-2 приёма пищи, увеличьте порции углеводов.",
                }
            )
        elif cal_pct < 85:
            alerts.append(
                {
                    "severity": "info",
                    "message": f"Небольшой недобор: {cal_pct:.0f}% от нормы.",
                    "action": "Увеличьте калорийность на 200-300 ккал/день.",
                }
            )

        prot_pct = (
            averages["proteins"] / profile.target_proteins * 100
            if profile.target_proteins > 0
            else 0
        )

        if prot_pct < 50:
            alerts.append(
                {
                    "severity": "critical",
                    "message": f"Острый дефицит белка: {averages['proteins']} из {profile.target_proteins} г.",
                    "action": f"Добавьте {profile.target_proteins - averages['proteins']:.0f} г белка: куриная грудка, творог, яйца, протеин.",
                }
            )
        elif prot_pct < 80:
            alerts.append(
                {
                    "severity": "warning",
                    "message": f"Недобор белка: {averages['proteins']} из {profile.target_proteins} г ({prot_pct:.0f}%).",
                    "action": "Добавьте 30-50 г белка в ежедневный рацион.",
                }
            )

        if averages["calories"] < 800 and len(days) > 0:
            alerts.append(
                {
                    "severity": "warning",
                    "message": "Потребление менее 800 ккал/день. Возможно, не все приёмы пищи записаны.",
                    "action": "Проверьте полноту заполнения дневника питания.",
                }
            )

        if 85 <= cal_pct <= 115:
            alerts.append(
                {"severity": "positive", "message": "Хорошее соблюдение калорийности."}
            )

        if prot_pct >= 90:
            alerts.append(
                {"severity": "positive", "message": "Отличное потребление белка."}
            )

        return alerts

    def _get_nutrition_trends(self, current_averages: dict) -> Optional[dict]:
        prev_queryset = EatenFood.objects.filter(
            user_id=self.user_id,
            eaten_at__date__range=(self.previous_start_date, self.previous_end_date),
        )

        prev_totals = FoodDataBuilder._eaten_food_range_days_total_list_build(
            prev_queryset, self.previous_start_date, self.previous_end_date
        )

        if not prev_totals:
            return None

        prev_days = len(prev_totals)
        prev_avgs = {
            "calories": sum(d["kcal"] for d in prev_totals.values()) / prev_days,
            "proteins": sum(d["proteins"] for d in prev_totals.values()) / prev_days,
            "fats": sum(d["fats"] for d in prev_totals.values()) / prev_days,
            "carbs": sum(d["carbohydrates"] for d in prev_totals.values()) / prev_days,
        }

        changes = {}
        for macro in self.MACROS:
            curr = current_averages[macro]
            prev = prev_avgs[macro]
            if prev > 0:
                pct = round((curr - prev) / prev * 100)
                changes[macro] = {
                    "change_percent": pct,
                    "direction": "up" if pct > 0 else "down" if pct < 0 else "stable",
                }

        return changes if changes else None

    # ============ ТРЕНИРОВКИ ============

    def _get_training_sessions(self):
        return TrainingSession.objects.filter(
            user_id=self.user_id,
            date_time__date__range=(self.start_date, self.end_date),
        ).order_by("date_time")

    def _build_training_section(self, sessions) -> dict:
        """Компактный раздел тренировок с учётом bodyweight и cardio"""
        if not sessions:
            return {"training_days": 0, "message": "Нет тренировок за период"}

        sessions_by_date = {}
        for s in sessions:
            date_str = s.date_time.date().isoformat()
            if date_str not in sessions_by_date:
                sessions_by_date[date_str] = []
            sessions_by_date[date_str].append(s)

        training_list = []
        total_volume = 0.0
        total_sets = 0
        muscle_usage = {}

        for date_str, day_sessions in sessions_by_date.items():
            for session in day_sessions:
                info = TrainingDataBuilder.get_training_session_info(session)
                stats = info["statistics"]

                # Получаем мышцы с НОВЫМ расчётом объёма
                session_muscles = self._get_session_muscles(session)

                # Обновляем общую статистику мышц
                for muscle, data in session_muscles.items():
                    if muscle not in muscle_usage:
                        muscle_usage[muscle] = {"sets": 0, "volume": 0.0, "sessions": 0}
                    muscle_usage[muscle]["sets"] += data["sets"]
                    muscle_usage[muscle]["volume"] += data["volume"]
                    muscle_usage[muscle]["sessions"] += 1

                # Считаем эффективный объём сессии
                session_effective_volume = sum(
                    data["volume"] for data in session_muscles.values()
                )

                session_data = {
                    "date": date_str,
                    "name": info["name"],
                    "duration_min": info["duration_minutes"],
                    "exercises": stats["workload"]["exercises"],
                    "sets": stats["workload"]["sets"],
                    "volume_kg": round(session_effective_volume, 1),
                    "muscles": list(session_muscles.keys()),
                }

                intensity = stats["performance"]["intensity_value"]
                if intensity > 0:
                    session_data["intensity_kg_per_min"] = intensity

                training_list.append(session_data)
                total_volume += session_effective_volume
                total_sets += stats["workload"]["sets"]

        section = {
            "training_days": len(sessions_by_date),
            "total_sessions": len(training_list),
            "total_volume_kg": round(total_volume, 1),
            "total_sets": total_sets,
            "sessions": training_list,
        }

        section["muscle_balance"] = self._analyze_muscle_balance(muscle_usage)
        section["alerts"] = self._build_training_alerts(
            training_list, muscle_usage, sessions_by_date
        )

        if self.config.include_previous_week:
            trends = self._get_training_trends(sessions, total_volume)
            if trends:
                section["vs_previous_week"] = trends

        return section

    def _calculate_effective_volume(
        self,
        completed_exercise,
        user_weight: Optional[float] = None,
    ) -> float:
        """
        Рассчитывает эффективный объём упражнения с учётом:
        - Силовые с весом: weight × reps
        - С собственным весом: bodyweight × coefficient × reps
        - Кардио: время × коэффициент
        - Плиометрика: bodyweight × coefficient × reps

        Returns: float — объём в кг
        """
        sets = completed_exercise.sets.all()
        ex = completed_exercise.base_exercise or completed_exercise.custom_exercise

        # Определяем тип упражнения
        exercise_type = ex.exercise_type if hasattr(ex, "exercise_type") else "STRENGTH"
        exercise_name = ex.name.upper() if ex and ex.name else ""

        # Базовый объём от дополнительного веса (если есть)
        weight_based_volume = sum(
            float(s.weight or 0) * (s.repetitions or 1) for s in sets
        )

        # Для упражнений с собственным весом и плиометрики
        if exercise_type in ("BODYWEIGHT", "CALISTHENICS", "PLYOMETRIC") or (
            exercise_type == "STRENGTH" and weight_based_volume == 0
        ):
            if user_weight and user_weight > 0:
                coefficient = BODYWEIGHT_EXERCISE_COEFFICIENTS.get(
                    exercise_name,
                    BODYWEIGHT_EXERCISE_COEFFICIENTS["DEFAULT_BODYWEIGHT"],
                )

                total_reps = sum(s.repetitions or 1 for s in sets)
                bodyweight_volume = user_weight * coefficient * total_reps

                return bodyweight_volume + weight_based_volume

        # Для кардио
        if exercise_type == "CARDIO":
            total_seconds = sum(s.duration_seconds or 0 for s in sets)
            total_minutes = total_seconds / 60

            coefficient = CARDIO_VOLUME_EQUIVALENT.get(
                exercise_name, CARDIO_VOLUME_EQUIVALENT["DEFAULT_CARDIO"]
            )

            cardio_volume = coefficient * total_minutes
            return cardio_volume + weight_based_volume

        # Обычные силовые — только дополнительный вес
        return weight_based_volume

    def _get_session_muscles(self, session) -> dict:
        """Извлекает группы мышц с учётом эффективного объёма"""
        profile = self._get_profile()
        user_weight = float(profile.weight) if profile and profile.weight else None

        muscles = {}
        for completed_ex in session.exercises.all():
            ex = completed_ex.base_exercise or completed_ex.custom_exercise
            muscle = (
                ex.primary_muscle_group if hasattr(ex, "primary_muscle_group") else None
            )
            if not muscle:
                continue

            sets_count = completed_ex.sets.count()
            # ИСПОЛЬЗУЕМ НОВЫЙ МЕТОД
            volume = self._calculate_effective_volume(
                completed_ex, user_weight=user_weight
            )

            if muscle not in muscles:
                muscles[muscle] = {"sets": 0, "volume": 0.0}
            muscles[muscle]["sets"] += sets_count
            muscles[muscle]["volume"] += volume

        return muscles

    def _analyze_muscle_balance(self, muscle_usage: dict) -> dict:
        if not muscle_usage:
            return {"note": "Нет данных о группах мышц"}

        total_sets = sum(m["sets"] for m in muscle_usage.values())

        balance = {}
        for muscle, data in muscle_usage.items():
            balance[muscle] = {
                "sets": data["sets"],
                "volume_kg": round(data["volume"], 1),
                "sessions": data["sessions"],
                "share_percent": (
                    round(data["sets"] / total_sets * 100) if total_sets > 0 else 0
                ),
            }

        trained_major = set(muscle_usage.keys()) & self.MAJOR_MUSCLE_GROUPS
        missing = self.MAJOR_MUSCLE_GROUPS - trained_major

        return {
            "by_muscle": balance,
            "missing_major_groups": list(missing) if missing else None,
            "balance_verdict": (
                (
                    "сбалансировано"
                    if len(missing) <= 1
                    else "не хватает проработки: " + ", ".join(missing)
                )
                if missing
                else "все основные группы задействованы"
            ),
        }

    def _build_training_alerts(
        self, training_list: list, muscle_usage: dict, sessions_by_date: dict
    ) -> list:
        alerts = []
        training_days = len(sessions_by_date)

        if training_days == 0:
            alerts.append(
                {
                    "severity": "warning",
                    "message": "Нет тренировок за неделю.",
                    "action": "Запланируйте хотя бы 2 тренировки на следующую неделю.",
                }
            )
        elif training_days < 2:
            alerts.append(
                {
                    "severity": "info",
                    "message": f"Всего {training_days} тренировочный день. Минимум для прогресса — 2-3.",
                    "action": "Добавьте ещё 1-2 тренировки на неделе.",
                }
            )
        elif training_days >= 4:
            alerts.append(
                {
                    "severity": "positive",
                    "message": f"Отличная частота: {training_days} тренировочных дней.",
                }
            )

        # Проверка прогрессивной перегрузки
        if len(training_list) >= 2:
            volumes = [t.get("volume_kg", 0) for t in training_list]
            if len(volumes) >= 2 and volumes[-1] < volumes[0] * 0.7:
                alerts.append(
                    {
                        "severity": "warning",
                        "message": "Объём тренировок снижается. Возможен застой.",
                        "action": "Попробуйте увеличить рабочие веса или количество подходов.",
                    }
                )

        return alerts

    def _get_training_trends(self, sessions, current_volume: float) -> Optional[dict]:
        prev_sessions = TrainingSession.objects.filter(
            user_id=self.user_id,
            date_time__date__range=(self.previous_start_date, self.previous_end_date),
        )

        if not prev_sessions:
            return None

        # Считаем объем прошлой недели через новый метод
        prev_volume = 0.0
        prev_days = set()
        for s in prev_sessions:
            session_muscles = self._get_session_muscles(s)
            session_volume = sum(data["volume"] for data in session_muscles.values())
            prev_volume += session_volume
            prev_days.add(s.date_time.date())

        changes = {
            "training_days": {
                "current": len(set(s.date_time.date() for s in sessions)),
                "previous": len(prev_days),
            },
            "volume_kg": {
                "current": round(current_volume, 1),
                "previous": round(prev_volume, 1),
            },
        }

        if prev_volume > 0:
            vol_change = round((current_volume - prev_volume) / prev_volume * 100)
            changes["volume_kg"]["change_percent"] = vol_change
            changes["volume_kg"]["direction"] = (
                "up" if vol_change > 5 else "down" if vol_change < -5 else "stable"
            )

        return changes

    # ============ ИТОГОВЫЙ ВЫВОД ============

    def _generate_summary(self, report: dict) -> str:
        parts = []

        nutrition = report.get("nutrition", {})
        if nutrition.get("data_available"):
            days = nutrition.get("days_logged", 0)
            avg_cal = nutrition.get("averages", {}).get("calories", 0)
            parts.append(f"🥗 Питание: {days}/7 дней, в среднем {avg_cal} ккал/день")

            compliance = nutrition.get("target_compliance", {})
            cal_info = compliance.get("calories", {})
            if cal_info:
                parts.append(
                    f"(цель: {cal_info.get('target', '—')} ккал, выполнено на {cal_info.get('percent', '—')}%)"
                )

        training = report.get("training", {})
        tr_days = training.get("training_days", 0)
        if tr_days > 0:
            parts.append(
                f"🏋️ Тренировки: {tr_days} дней, {training.get('total_sessions', 0)} сессий"
            )
            vol = training.get("total_volume_kg", 0)
            if vol > 0:
                parts.append(f"(общий объём: {vol} кг)")

        return " | ".join(parts) if parts else "Недостаточно данных для анализа"
