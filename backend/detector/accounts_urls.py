from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .accounts_api import MeView, MyProjectsView, ProjectDetailView, RegenerateTokenView, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("token/", TokenObtainPairView.as_view(), name="auth-token"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("projects/", MyProjectsView.as_view(), name="my-projects"),
    path("projects/<slug:slug>/", ProjectDetailView.as_view(), name="my-project-detail"),
    path("projects/<slug:slug>/regenerate-token/", RegenerateTokenView.as_view(), name="my-project-regen-token"),
]