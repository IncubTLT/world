from django.urls import path

from .views import (
    AIHistoryView,
    ClearHistoryView,
    GptModelPriceView,
    UserModelsProfileView,
)

app_name = "ai"

urlpatterns = [
    path("history/", AIHistoryView.as_view(), name="history"),
    path("history/clear/", ClearHistoryView.as_view(), name="history-clear"),
    path("profile/", UserModelsProfileView.as_view(), name="profile"),
    path("models/<int:pk>/price/", GptModelPriceView.as_view(), name="model-price"),
]
