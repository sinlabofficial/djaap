from django.urls import path

from . import views

app_name = "example"

urlpatterns = [
    path("", views.ItemListView.as_view(), name="list"),
    path("create/", views.ItemCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.ItemDetailView.as_view(), name="detail"),
    path("<uuid:pk>/update/", views.ItemUpdateView.as_view(), name="update"),
    path("<uuid:pk>/delete/", views.ItemDeleteView.as_view(), name="delete"),
]
