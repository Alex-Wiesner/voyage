from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CapabilitiesView,
    ChatProviderCatalogViewSet,
    ChatViewSet,
    DaySuggestionsView,
)

router = DefaultRouter()
router.register(r"conversations", ChatViewSet, basename="chat-conversation")
router.register(
    r"providers", ChatProviderCatalogViewSet, basename="chat-provider-catalog"
)

urlpatterns = [
    path("", include(router.urls)),
    path("capabilities/", CapabilitiesView.as_view(), name="chat-capabilities"),
    path("suggestions/day/", DaySuggestionsView.as_view(), name="chat-day-suggestions"),
]
