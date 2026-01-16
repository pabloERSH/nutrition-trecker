from rest_framework import viewsets, status
from rest_framework.views import APIView
from training import models, serializers
from django_filters.rest_framework import DjangoFilterBackend
from common.filters.FuzzySearchFilter import FuzzySearchFilter
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from common.permissions.IsOwner403Permission import IsOwner403Permission
from common.mixins.AutocompleteMixin import AutocompleteMixin
from django.core.cache import cache
from training.services.TrainingDataBuilder import TrainingDataBuilder
from common.utils.CacheHelper import CacheHelper


class BaseExerciseViewSet(AutocompleteMixin, viewsets.ReadOnlyModelViewSet):
    queryset = models.BaseExercise.objects.all()

    filter_backends = [DjangoFilterBackend, FuzzySearchFilter]
    filterset_fields = ["primary_muscle_group", "exercise_type", "equipment_type"]
    search_fields = ["name"]

    def get_serializer_class(self):
        """Выбираем сериализатор в зависимости от действия"""
        if self.action == "retrieve":
            return serializers.BaseExerciseDetailSerializer
        return serializers.BaseExerciseListSerializer

    def list(self, request, *args, **kwargs):
        cache_key = CacheHelper.make_cache_key(
            "base_exercises", f"list:{request.get_full_path()}"
        )

        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)

            cache.set(cache_key, paginated_response.data, 60 * 60 * 24 * 7)  # 7 дней
            return paginated_response

        serializer = self.get_serializer(queryset, many=True)
        cache.set(cache_key, serializer.data, 60 * 60 * 24 * 7)  # 7 дней
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance_id = kwargs.get("pk")

        cache_key = CacheHelper.make_cache_key("base_exercise", f"detail_{instance_id}")

        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        instance = self.get_object()
        serializer = self.get_serializer(instance)
        cache.set(cache_key, serializer.data, 60 * 60 * 24 * 7)  # 7 дней

        return Response(serializer.data, status=status.HTTP_200_OK)


class CustomExerciseViewSet(AutocompleteMixin, viewsets.ModelViewSet):
    serializer_class = serializers.CustomExerciseSerializer
    permission_classes = [IsOwner403Permission]

    filter_backends = [DjangoFilterBackend, FuzzySearchFilter]
    filterset_fields = ["primary_muscle_group", "exercise_type", "equipment_type"]
    search_fields = ["name"]

    def get_queryset(self):
        return models.CustomExercise.objects.filter(
            user_id=self.request.user.telegram_id
        )

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)

    def perform_update(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)

    def list(self, request, *args, **kwargs):
        user_id = request.user.telegram_id
        cache_key = CacheHelper.make_cache_key(
            "custom_exercises", f"list:{request.get_full_path()}", user_id
        )

        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)

            cache.set(cache_key, paginated_response.data, 60 * 60 * 24)  # 1 день
            return paginated_response

        serializer = self.get_serializer(queryset, many=True)
        cache.set(cache_key, serializer.data, 60 * 60 * 24)  # 1 день
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance_id = kwargs.get("pk")
        user_id = request.user.telegram_id
        cache_key = CacheHelper.make_cache_key(
            "custom_exercise", f"detail_{instance_id}", user_id
        )

        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        instance = self.get_object()
        serializer = self.get_serializer(instance)
        cache.set(cache_key, serializer.data, 60 * 60 * 24 * 2)  # 2 дней

        return Response(serializer.data, status=status.HTTP_200_OK)


class TrainingSessionViewSet(AutocompleteMixin, viewsets.ModelViewSet):
    serializer_class = serializers.TrainingSessionSerializer
    permission_classes = [IsOwner403Permission]
    filter_backends = [FuzzySearchFilter]
    search_fields = ["name", "description"]
    autocomplete_search_fields = ["name"]

    def get_queryset(self):
        return models.TrainingSession.objects.filter(
            user_id=self.request.user.telegram_id
        )

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)

    def perform_update(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)

    def list(self, request, *args, **kwargs):
        user_id = request.user.telegram_id
        cache_key = CacheHelper.make_cache_key(
            "training_sessions", f"list:{request.get_full_path()}", user_id
        )
        training_sessions = cache.get(cache_key)
        if training_sessions:
            return Response(training_sessions, status=status.HTTP_200_OK)
        else:
            training_sessions = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(training_sessions, many=True)
            cache.set(cache_key, serializer.data, 60 * 30)  # 30 минут
            return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance_id = kwargs.get("pk")
        user_id = request.user.telegram_id
        cache_key = CacheHelper.make_cache_key(
            "training_session", f"detail_{instance_id}", user_id
        )

        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        instance = self.get_object()
        training_session_data = TrainingDataBuilder.get_training_session_info(instance)
        cache.set(cache_key, training_session_data, 60 * 30)  # 30 минут

        return Response(training_session_data, status=status.HTTP_200_OK)


class CompletedExerciseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOwner403Permission]

    def get_serializer_class(self):
        if self.action == "create":
            return serializers.CompletedExerciseCreateSerializer
        if self.action == "retrieve":
            return serializers.CompletedExerciseDetailSerializer
        return serializers.CompletedExerciseListSerializer

    def _get_training_session(self):
        return get_object_or_404(
            models.TrainingSession,
            id=self.kwargs.get("session_pk"),
            user_id=self.request.user.telegram_id,
        )

    def get_queryset(self):
        training_session = self._get_training_session()
        qs = training_session.exercises.select_related(
            "base_exercise",
            "custom_exercise",
        )

        if self.action == "retrieve":
            qs = qs.prefetch_related("sets")

        return qs

    def perform_create(self, serializer):
        serializer.save(
            training_session=self._get_training_session(),
            user_id=self.request.user.telegram_id,
        )

    def perform_update(self, serializer):
        serializer.save(
            training_session=self._get_training_session(),
            user_id=self.request.user.telegram_id,
        )

    def list(self, request, *args, **kwargs):
        user_id = request.user.telegram_id
        training_session_pk = self.kwargs.get("session_pk")
        cache_key = CacheHelper.make_cache_key(
            f"completed_exercises:training_session_id:{training_session_pk}",
            "list",
            user_id,
        )
        completed_exercises = cache.get(cache_key)
        if completed_exercises:
            return Response(completed_exercises, status=status.HTTP_200_OK)
        else:
            completed_exercises = self.get_queryset()
            serializer = self.get_serializer(completed_exercises, many=True)
            cache.set(cache_key, serializer.data, 60 * 30)  # 30 минут
            return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance_id = kwargs.get("pk")
        user_id = request.user.telegram_id
        cache_key = CacheHelper.make_cache_key(
            "completed_exercise", f"detail_{instance_id}", user_id
        )

        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        instance = self.get_object()
        completed_exericse = self.get_serializer(instance)
        cache.set(cache_key, completed_exericse.data, 60 * 30)  # 30 минут

        return Response(completed_exericse.data, status=status.HTTP_200_OK)


class ExerciseSetViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.ExerciseSetSerializer
    permission_classes = [IsOwner403Permission]

    def _get_completed_exercise(self):
        return get_object_or_404(
            models.CompletedExercise,
            id=self.kwargs["completed_exercise_pk"],
            training_session_id=self.kwargs["session_pk"],
            user_id=self.request.user.telegram_id,
        )

    def get_queryset(self):
        return self._get_completed_exercise().sets.all()

    def perform_create(self, serializer):
        serializer.save(
            completed_exercise=self._get_completed_exercise(),
            user_id=self.request.user.telegram_id,
        )

    def perform_update(self, serializer):
        serializer.save(
            completed_exercise=self._get_completed_exercise(),
            user_id=self.request.user.telegram_id,
        )


class TagsView(APIView):
    def get(self, request):
        cache_key = "tags"
        data = cache.get(cache_key)

        if not data:
            data = {
                "muscle_groups": [
                    {"value": k, "label": v} for k, v in models.MUSCLE_GROUP_CHOICES
                ],
                "exercise_types": [
                    {"value": k, "label": v} for k, v in models.EXERCISE_TYPE_CHOICES
                ],
                "equipment_types": [
                    {"value": k, "label": v} for k, v in models.EQUIPMENT_CHOICES
                ],
            }
            cache.set(cache_key, data, 60 * 60 * 24 * 7)

        return Response(data)
