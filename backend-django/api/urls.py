from django.urls import path, include
from rest_framework import routers
from .views import CattleViewSet, DiagnosisViewSet, RegisterView, MeView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = routers.DefaultRouter()
router.register(r"cattle", CattleViewSet, basename="cattle")
router.register(r"diagnosis", DiagnosisViewSet, basename="diagnosis")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
]
