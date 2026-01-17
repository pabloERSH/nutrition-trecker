from rest_framework import serializers
from training import models
from common.custom.OwnedPrimaryKeyRelatedField import OwnedPrimaryKeyRelatedField
from django.conf import settings


class ExerciseImageMixin:
    fallback_path = settings.MEDIA_URL + "photos/fallbacks/exercise_fallback.jpg"

    def _abs(self, path):
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path

    def get_thumbnail_url(self, obj):
        """
        Универсальный метод:
        - BaseExercise → thumbnail / image
        - CustomExercise → fallback
        """
        # BaseExercise имеет image_thumbnail
        if hasattr(obj, "image_thumbnail"):
            if obj.image_thumbnail:
                return self._abs(obj.image_thumbnail.url)
            if obj.image:
                return self._abs(obj.image.url)

        return self._abs(self.fallback_path)

    def get_fallback_url(self):
        return self._abs(self.fallback_path)


class ExerciseCommonMixin:
    def get_muscle_groups_info(self, obj):
        """Возвращает информацию о группах мышц"""
        # Используем встроенные методы Django get_FOO_display()
        primary_display = obj.get_primary_muscle_group_display()
        secondary_display = (
            obj.get_secondary_muscle_group_display()
            if obj.secondary_muscle_group
            else None
        )

        return {
            "primary": {
                "code": obj.primary_muscle_group,
                "display": primary_display,
            },
            "secondary": (
                {
                    "code": obj.secondary_muscle_group,
                    "display": secondary_display,
                }
                if obj.secondary_muscle_group
                else None
            ),
        }

    def get_exercise_type_info(self, obj):
        """Возвращает информацию о типе упражнения"""
        return {
            "code": obj.exercise_type,
            "display": obj.get_exercise_type_display(),
        }

    def get_equipment_type_info(self, obj):
        """Возвращает информацию о требуемом тренировочном оборудовании"""
        return {
            "code": obj.equipment_type,
            "display": obj.get_equipment_type_display(),
        }


class CompletedExerciseMixin:
    def get_source_type(self, obj):
        return obj.get_type()

    def get_source_image(self, obj):
        request = self.context.get("request")

        if obj.base_exercise:
            serializer = BaseExerciseListSerializer(
                obj.base_exercise, context={"request": request}
            )
            return serializer.data["thumbnail_url"]

        fallback_path = "/photos/fallbacks/exercise_fallback.jpg"
        return request.build_absolute_uri(fallback_path) if request else fallback_path

    def get_source_data(self, obj):
        type = obj.get_type()
        data = None

        match type:
            case "base":
                data = {
                    "base_exercise_id": obj.base_exercise.id,
                    "name": obj.base_exercise.name,
                    "primary_muscle_group": obj.base_exercise.primary_muscle_group,
                    "secondary_muscle_group": obj.base_exercise.secondary_muscle_group,
                    "exercise_type": obj.base_exercise.exercise_type,
                }
            case "custom":
                data = {
                    "custom_exercise_id": obj.custom_exercise.id,
                    "name": obj.custom_exercise.name,
                    "primary_muscle_group": obj.custom_exercise.primary_muscle_group,
                    "secondary_muscle_group": obj.custom_exercise.secondary_muscle_group,
                    "exercise_type": obj.custom_exercise.exercise_type,
                }

        return data


class BaseExerciseListSerializer(
    ExerciseCommonMixin, ExerciseImageMixin, serializers.ModelSerializer
):
    """ДЛЯ списка упражнений (list)"""

    thumbnail_url = serializers.SerializerMethodField()
    muscle_groups_info = serializers.SerializerMethodField()
    exercise_type_info = serializers.SerializerMethodField()
    equipment_type_info = serializers.SerializerMethodField()

    class Meta:
        model = models.BaseExercise
        fields = [
            "id",
            "name",
            "muscle_groups_info",
            "exercise_type_info",
            "equipment_type_info",
            "thumbnail_url",
        ]
        read_only_fields = fields


class BaseExerciseDetailSerializer(
    ExerciseCommonMixin, ExerciseImageMixin, serializers.ModelSerializer
):
    """ДЛЯ конкретного упражнения (retrieve)"""

    thumbnail_url = serializers.SerializerMethodField()
    muscle_groups_info = serializers.SerializerMethodField()
    exercise_type_info = serializers.SerializerMethodField()
    equipment_type_info = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        """URL полноразмерного изображения"""
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return self.get_fallback_url()

    class Meta:
        model = models.BaseExercise
        fields = [
            "id",
            "name",
            "description",
            "muscle_groups_info",
            "exercise_type_info",
            "equipment_type_info",
            "thumbnail_url",
            "image_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CustomExerciseSerializer(
    ExerciseCommonMixin, ExerciseImageMixin, serializers.ModelSerializer
):
    muscle_groups_info = serializers.SerializerMethodField()
    exercise_type_info = serializers.SerializerMethodField()
    equipment_type_info = serializers.SerializerMethodField()

    primary_muscle_group = serializers.ChoiceField(
        choices=models.MUSCLE_GROUP_CHOICES, write_only=True
    )
    secondary_muscle_group = serializers.ChoiceField(
        choices=models.MUSCLE_GROUP_CHOICES,
        required=False,
        allow_null=True,
        write_only=True,
    )
    exercise_type = serializers.ChoiceField(
        choices=models.EXERCISE_TYPE_CHOICES, write_only=True
    )
    equipment_type = serializers.ChoiceField(
        choices=models.EQUIPMENT_CHOICES, write_only=True
    )

    class Meta:
        model = models.CustomExercise
        fields = [
            "id",
            "user_id",
            "name",
            "muscle_groups_info",
            "exercise_type_info",
            "equipment_type_info",
            "primary_muscle_group",
            "secondary_muscle_group",
            "exercise_type",
            "equipment_type",
            "description",
            "updated_at",
            "created_at",
        ]
        read_only_fields = ["id", "user_id", "created_at", "updated_at"]
        write_only_fields = [
            "exercise_type",
            "equipment_type",
            "primary_muscle_group",
            "secondary_muscle_group",
        ]


class CompletedExerciseListSerializer(
    CompletedExerciseMixin, serializers.ModelSerializer
):
    source_type = serializers.SerializerMethodField(read_only=True)
    source_data = serializers.SerializerMethodField(read_only=True)
    source_image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.CompletedExercise
        fields = [
            "id",
            "user_id",
            "training_session",
            "source_type",
            "source_data",
            "source_image",
            "comment",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "training_session",
            "source_type",
            "source_data",
            "source_image",
            "created_at",
            "updated_at",
        ]  # user_id задаем во view через self.request.user


class CompletedExerciseCreateSerializer(serializers.ModelSerializer):
    base_exercise_id = serializers.PrimaryKeyRelatedField(
        queryset=models.BaseExercise.objects.all(),
        source="base_exercise",
        required=False,
        write_only=True,
    )

    custom_exercise_id = OwnedPrimaryKeyRelatedField(
        queryset=models.CustomExercise.objects.all(),
        source="custom_exercise",
        required=False,
        write_only=True,
        owner_field="user_id",
    )

    class Meta:
        model = models.CompletedExercise
        fields = [
            "id",
            "base_exercise_id",
            "custom_exercise_id",
            "comment",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if not attrs.get("base_exercise") and not attrs.get("custom_exercise"):
            raise serializers.ValidationError(
                "Нужно указать base_exercise_id или custom_exercise_id"
            )
        if attrs.get("base_exercise") and attrs.get("custom_exercise"):
            raise serializers.ValidationError(
                "Можно указать только одно из: base_exercise_id или custom_exercise_id"
            )
        return attrs


class ExerciseSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ExerciseSet
        fields = [
            "id",
            "user_id",
            "completed_exercise",
            "repetitions",
            "weight",
            "duration_seconds",
            "distance_meters",
            "rest_after_set",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "completed_exercise",
            "created_at",
            "updated_at",
        ]  # user_id задаем во view через self.request.user


class CompletedExerciseDetailSerializer(
    CompletedExerciseMixin, serializers.ModelSerializer
):
    source_type = serializers.SerializerMethodField()
    source_data = serializers.SerializerMethodField()
    source_image = serializers.SerializerMethodField()
    sets = ExerciseSetSerializer(many=True, read_only=True)

    class Meta:
        model = models.CompletedExercise
        fields = [
            "id",
            "source_type",
            "source_image",
            "source_data",
            "comment",
            "sets",
            "created_at",
            "updated_at",
        ]


class TrainingSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TrainingSession
        fields = [
            "id",
            "user_id",
            "date_time",
            "duration",
            "name",
            "description",
        ]
        read_only_fields = ["id", "user_id", "created_at", "updated_at"]
