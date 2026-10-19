from django.contrib.auth.decorators import login_required
from django.urls import path

from badges import views

urlpatterns = [
    path("badges/", login_required(views.BadgeList.as_view()), name="badge_list"),
    path("badges/leaderboard/", login_required(views.Leaderboard.as_view()), name="badge_leaderboard"),
    path("tech-rider/", login_required(views.TechRider.as_view()), name="tech_rider"),
    path("tech-rider/<int:pk>/", login_required(views.TechRider.as_view()), name="tech_rider"),
]
