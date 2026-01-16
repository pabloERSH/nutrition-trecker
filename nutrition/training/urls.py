from rest_framework import routers
from rest_framework_nested import routers as nested_routers
from training import views
from django.urls import path, include


router = routers.DefaultRouter()
router.register(r"base-exercises", views.BaseExerciseViewSet, basename="base-exercises")
router.register(
    r"custom-exercises", views.CustomExerciseViewSet, basename="custom-exercises"
)
router.register(r"sessions", views.TrainingSessionViewSet, basename="sessions")
sessions_router = nested_routers.NestedDefaultRouter(
    router, r"sessions", lookup="session"
)
sessions_router.register(
    r"completed-exercises",
    views.CompletedExerciseViewSet,
    basename="completed-exercises",
)
completed_exercises_router = nested_routers.NestedDefaultRouter(
    sessions_router, r"completed-exercises", lookup="completed_exercise"
)
completed_exercises_router.register(r"sets", views.ExerciseSetViewSet, basename="sets")


urlpatterns = [
    path("training/", include(router.urls)),
    path("training/", include(sessions_router.urls)),
    path("training/", include(completed_exercises_router.urls)),
    path("training/tags/", views.TagsView.as_view()),
]
