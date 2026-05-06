from django.urls import path
from .views import UserProfileDetailView

urlpatterns = [
    path("profile/", UserProfileDetailView.as_view(), name="user-profile"),
]
