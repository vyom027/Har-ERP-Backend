from django.urls import path
from . import views

app_name = "inward"

urlpatterns = [
    path("", views.inward_list, name="inward_list"),
    path("add/", views.inward_create, name="inward_create"),
    path("edit/<int:pk>/", views.inward_update, name="inward_update"),
    path("delete/<int:pk>/", views.inward_delete, name="inward_delete"),
]
