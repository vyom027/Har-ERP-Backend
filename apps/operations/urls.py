from django.urls import path
from . import views

app_name = 'operations'

urlpatterns = [
    path('', views.op_list, name='list'),
    path('update-name/', views.update_operation_name, name='inline_update_operation_name'),
]
