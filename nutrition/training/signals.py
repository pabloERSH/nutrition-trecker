from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging
from training.models import (
    BaseExercise,
    CustomExercise,
    CompletedExercise,
    TrainingSession,
)
from common.utils.CacheHelper import CacheHelper


logger = logging.getLogger("nutrition")


@receiver([post_save, post_delete], sender=BaseExercise)
def invalidate_base_exercise_cache(sender, instance, **kwargs):
    CacheHelper.bump_cache_version("base_exercises")
    CacheHelper.bump_cache_version("base_exercise")
    logger.info("BaseExercise version bumped (global)")


@receiver([post_save, post_delete], sender=CustomExercise)
def invalidate_custom_exercise_cache(sender, instance, **kwargs):
    user_id = instance.user_id
    CacheHelper.bump_cache_version("custom_exercises", user_id)
    CacheHelper.bump_cache_version("custom_exercise", user_id)
    logger.info(f"CustomExercise version bumped for user {user_id}")


@receiver([post_save, post_delete], sender=TrainingSession)
def invalidate_session_cache(sender, instance, **kwargs):
    user_id = instance.user_id
    CacheHelper.bump_cache_version("training_session", user_id)
    CacheHelper.bump_cache_version("training_sessions", user_id)
    logger.info(f"TrainingSession version bumped for user {user_id}")


@receiver([post_save, post_delete], sender=CompletedExercise)
def invalidate_completed_exercise_cache(sender, instance, **kwargs):
    user_id = instance.user_id
    CacheHelper.bump_cache_version("completed_exercises", user_id)
    CacheHelper.bump_cache_version("completed_exercise", user_id)

    CacheHelper.bump_cache_version("training_session", user_id)
    logger.info(
        f"CompletedExercise & TrainingSession version bumped for user {user_id}"
    )
