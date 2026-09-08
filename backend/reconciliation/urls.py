from django.urls import path

from reconciliation.views import DisagreementListView


urlpatterns = [
    path("disagreements/", DisagreementListView.as_view(), name="disagreement-list"),
]
