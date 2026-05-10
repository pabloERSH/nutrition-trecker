from django.urls import path
from .views import UserProfileDetailView, weekly_report_view

urlpatterns = [
    path("profile/", UserProfileDetailView.as_view(), name="user-profile"),
    path("profile/report/weekly/", weekly_report_view, name="weekly-report"),
]
