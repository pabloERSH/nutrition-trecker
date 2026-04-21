from rest_framework import viewsets, status
from rest_framework.views import APIView
from training import models, serializers
from django_filters.rest_framework import DjangoFilterBackend
from common.filters.FuzzySearchFilter import FuzzySearchFilter
from common.filters.OneDateFilter import OneDateFilter
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from common.permissions.IsOwner403Permission import IsOwner403Permission
from common.mixins.AutocompleteMixin import AutocompleteMixin
from django.core.cache import cache
from training.services.TrainingDataBuilder import TrainingDataBuilder
from common.decorators.cache_response import cache_response


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

    @cache_response(
        entity="base_exercise",
        ttl=60 * 60,
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @cache_response(
        entity="base_exercise",
        ttl=60 * 60 * 24 * 7,
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


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

    @cache_response(
        entity="custom_exercise",
        ttl=60 * 30,
        per_user=True,
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @cache_response(
        entity="custom_exercise",
        ttl=60 * 60 * 24 * 2,
        per_user=True,
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class TrainingSessionViewSet(AutocompleteMixin, viewsets.ModelViewSet):
    serializer_class = serializers.TrainingSessionSerializer
    permission_classes = [IsOwner403Permission]
    filter_backends = [OneDateFilter]

    def get_queryset(self):
        return models.TrainingSession.objects.filter(
            user_id=self.request.user.telegram_id
        )

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)

    def perform_update(self, serializer):
        serializer.save(user_id=self.request.user.telegram_id)

    @cache_response(
        entity="training_session",
        ttl=60 * 30,
        per_user=True,
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @cache_response(
        entity="training_session",
        ttl=60 * 30,
        per_user=True,
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = TrainingDataBuilder.get_training_session_info(instance)
        return Response(data)


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

    @cache_response(
        entity="completed_exercise",
        ttl=60 * 30,
        per_user=True,
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @cache_response(entity="completed_exercise", ttl=60 * 30, per_user=True)
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


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

    @cache_response(entity="exercise_set", ttl=60 * 30, per_user=True)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @cache_response(entity="exercise_set", ttl=60 * 30, per_user=True)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


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
