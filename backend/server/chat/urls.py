from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChatProviderCatalogViewSet, ChatViewSet

router = DefaultRouter()
router.register(r"conversations", ChatViewSet, basename="chat-conversation")
router.register(
    r"providers", ChatProviderCatalogViewSet, basename="chat-provider-catalog"
)

urlpatterns = [
    path("", include(router.urls)),
]
